package main

import (
	"./appsinstalled"
	"bufio"
	"compress/gzip"
	"context"
	"errors"
	"flag"
	"fmt"
	"github.com/bradfitz/gomemcache/memcache"
	"github.com/golang/protobuf/proto"
	"golang.org/x/sync/semaphore"
	"log"
	"os"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

const (
	MaxActiveGoroutines = 1000
	MaxMemcConns        = 10
	NormalErrRate       = 0.01
)

type CommandArgs struct {
	test         bool
	dry          bool
	logPath      string
	filesPattern string

	idfa string
	gaid string
	adid string
	dvid string
}

type MemcachedClient struct {
	addr string
	client memcache.Client
	sem    semaphore.Weighted
}

type AppsInstalled struct {
	devType string
	devId   string
	lat     float64
	lon     float64
	apps    []uint32
}

func main() {
	comArgs := parseArgs()

	logfile, err := os.OpenFile(comArgs.logPath, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0644)
	if err != nil {
		log.Fatalf("Cannot open log file: %s", comArgs.logPath)
		return
	}
	log.SetOutput(logfile)
	defer logfile.Close()

	if comArgs.test {
		prototest()
		return
	}

	memcClients := createMemcachedClientsMap(comArgs)

	files, err := filepath.Glob(comArgs.filesPattern)
	if err != nil || len(files) < 1 {
		log.Fatalf("Files by pattern %v not found. Exit", comArgs.filesPattern)
		return
	}

	for _, filePath := range files {
		processFile(filePath, memcClients, comArgs.dry)
	}
}

func prototest() {
	sample := "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\ngaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"

	for _, line := range strings.Split(sample, "\n") {
		appsInstalled, _ := parseLine(line)
		ua := &appsinstalled.UserApps{
			Lat:  proto.Float64(appsInstalled.lat),
			Lon:  proto.Float64(appsInstalled.lon),
			Apps: appsInstalled.apps,
		}
		packed, err := proto.Marshal(ua)
		if err != nil {
			log.Fatalf("prototest error: can't Marshal ua")
			os.Exit(1)
		}

		unpacked := &appsinstalled.UserApps{}
		err = proto.Unmarshal(packed, unpacked)
		if err != nil {
			log.Fatalf("prototest error: can't Unmarshal packed ua")
			os.Exit(1)
		}

		badLat := unpacked.GetLat() != ua.GetLat()
		badLon := unpacked.GetLon() != ua.GetLon()
		badApps := !reflect.DeepEqual(ua.GetApps(), unpacked.GetApps())
		if badLat || badLon || badApps {
			log.Fatalf("prototest error: unpacked and ua values are different")
			os.Exit(1)
		}
	}
	log.Print("prototest success")
	os.Exit(0)
}

func createMemcachedClientsMap(comArgs CommandArgs) map[string]MemcachedClient {
	memcClients := make(map[string]MemcachedClient)
	memcClients["idfa"] = MemcachedClient{
		comArgs.idfa,
		*memcache.New(comArgs.idfa),
		*semaphore.NewWeighted(int64(MaxMemcConns)),
	}
	memcClients["gaid"] = MemcachedClient{
		comArgs.gaid,
		*memcache.New(comArgs.gaid),
		*semaphore.NewWeighted(int64(MaxMemcConns)),
	}
	memcClients["adid"] = MemcachedClient{
		comArgs.adid,
		*memcache.New(comArgs.adid),
		*semaphore.NewWeighted(int64(MaxMemcConns)),
	}
	memcClients["dvid"] = MemcachedClient{
		comArgs.dvid,
		*memcache.New(comArgs.dvid),
		*semaphore.NewWeighted(int64(MaxMemcConns)),
	}

	return memcClients
}

func parseArgs() CommandArgs {
	isTest := flag.Bool("test", false, "test protobuf")
	isDry := flag.Bool("dry", false, "debug mode (without sending to memcached)")
	logPath := flag.String("log", "./memc.log", "path to log file")
	filesPattern := flag.String("pattern", "/data/appsinstalled/*.tsv.gz", "files path pattern")

	idfa := flag.String("idfa", "127.0.0.1:33013", "ip and port of idfa memcached server")
	gaid := flag.String("gaid", "127.0.0.1:33014", "ip and port of gaid memcached server")
	adid := flag.String("adid", "127.0.0.1:33015", "ip and port of adid memcached server")
	dvid := flag.String("dvid", "127.0.0.1:33016", "ip and port of dvid memcached server")

	flag.Parse()

	comArgs := CommandArgs{
		*isTest,
		*isDry,
		*logPath,
		*filesPattern,

		*idfa,
		*gaid,
		*adid,
		*dvid,
	}

	return comArgs
}

// Read file line by line
// Parse each line to AppsInstalled struct and send it to MemcachedClient
// Count errors from goroutines in separate goroutine
// Help Links:
// https://golang.org/pkg/sync/#WaitGroup
// https://play.golang.org/p/uvQMci2ru5E
func processFile(filePath string, memcClients map[string]MemcachedClient, dry bool) {
	log.Printf("%v: start processing", filePath)

	processed, errorsCount := 0, 0

	// Run goroutine for counting errors from other goroutines-workers
	errorsCh := make(chan int)
	sentinel := make(chan int)
	go countErrors(errorsCh, sentinel)

	file, err := os.Open(filePath)
	if err != nil {
		log.Fatalf("Can't open file: %v", err)
		sentinel <- 0
		return
	}
	defer file.Close()

	gz, err := gzip.NewReader(file)
	if err != nil {
		log.Printf("Can't create a new Reader %v", err)
		return
	}
	defer gz.Close()

	// Read file and parse every line in loop.
	// For every success parsed line create goroutine updateMemcache
	// There can't be goroutines more than MaxActiveGoroutines
	// and connections more than MaxMemcConns for each memcClient
	// at the same time
	var wgr sync.WaitGroup
	var activeGoroutines uint32
	scanner := bufio.NewScanner(gz)
	for scanner.Scan() {
		line := scanner.Text()
		if len(line) < 1 {
			continue
		}

		ai, err := parseLine(line)
		if err != nil {
			errorsCount += 1
			continue
		}

		memcClient, ok := memcClients[ai.devType]
		if !ok {
			errorsCount += 1
			log.Printf("Unknown device type: %v", ai.devType)
			continue
		}

		for {
			activeGoroutinesNow := atomic.LoadUint32(&activeGoroutines)
			if activeGoroutinesNow < MaxActiveGoroutines {
				break
			}
			time.Sleep(100 * time.Millisecond)
		}
		go memcClient.updateMemcache(ai, &activeGoroutines, errorsCh, dry)

		processed += 1
		if processed%10000 == 0 {
			log.Printf("%v: ready %v lines", filePath, processed)
		}
	}

	wgr.Wait()

	sentinel <- 0
	errCount := <-errorsCh
	processed -= errCount
	errorsCount += errCount

	if processed > 0 {
		errRate := float64(errorsCount) / float64(processed)
		if errRate <= NormalErrRate {
			log.Printf("%v: Success. Error rate (%v)", filePath, errRate)
		} else {
			log.Fatalf("%v: Fail. Error rate (%v)", filePath, errRate)
		}

	}
	renameFile(filePath)
}

// Count errors from updateMemcache goroutines
// Exit, when receive sentinel
// Help Links:
// https://go-tour-ru-ru.appspot.com/concurrency/5
func countErrors(errorsCh chan int, sentinel chan int) {
	var errorsCount int
	for {
		select {
		case <-errorsCh:
			errorsCount += 1
		case <-sentinel:
			errorsCh <- errorsCount
			return
		}
	}
}

// Update mc with ai value
// Help Links:
// https://gobyexample.com/atomic-counters
// https://play.golang.org/p/6eFjx029Tmm
// https://godoc.org/golang.org/x/sync/semaphore
func (mc *MemcachedClient) updateMemcache(ai AppsInstalled, activeGr *uint32, errorsCh chan int, dry bool) {
	atomic.AddUint32(activeGr, 1)
	defer atomic.AddUint32(activeGr, ^uint32(0))

	ua := &appsinstalled.UserApps{
		Lat:  proto.Float64(ai.lat),
		Lon:  proto.Float64(ai.lon),
		Apps: ai.apps,
	}
	key := fmt.Sprintf("%s:%s", ai.devType, ai.devId)
	packed, _ := proto.Marshal(ua)

	if dry {
		log.Printf("%s -> %s", key, mc.addr)
	} else {
		ctx := context.TODO()
		err := mc.sem.Acquire(ctx, 1)
		if err != nil {
			log.Fatalf("Can't acquire semaphore for: %v", mc.addr)
			errorsCh <- 1
			return
		}

		err = mc.client.Set(&memcache.Item{
			Key: key,
			Value: packed,
		})
		if err != nil {
			log.Fatalf("Can't set %s to memc: %s", key, mc.addr)
			errorsCh <- 1
			return
		}
		mc.sem.Release(1)
	}
}

// Parse line from file to AppsInstalled struct
// Return error if can't parse line
func parseLine(line string) (AppsInstalled, error) {
	var ai AppsInstalled

	lineParts := strings.Split(strings.TrimSpace(line), "\t")

	if len(lineParts) < 5 {
		return ai, errors.New("malformed line")
	}
	if len(lineParts[0]) == 0 || len(lineParts[1]) == 0 {
		return ai, errors.New("malformed line")
	}

	appsStrSlice := strings.Split(lineParts[4], ",")
	var appsIntSlice []uint32
	var hasError bool
	for _, appStr := range appsStrSlice {
		appInt, err := strconv.Atoi(appStr)
		if err != nil {
			hasError = true
		} else {
			appsIntSlice = append(appsIntSlice, uint32(appInt))
		}
	}
	if hasError {
		log.Fatalf("Not all user apps are digits: %v", line)
	}

	lat, err := strconv.ParseFloat(lineParts[2], 64)
	lon, err := strconv.ParseFloat(lineParts[3], 64)
	if err != nil {
		log.Fatalf("Invalid geo coords: %v", line)
	}

	ai = AppsInstalled{
		devType: lineParts[0],
		devId:   lineParts[1],
		apps:    appsIntSlice,
		lat:     lat,
		lon:     lon,
	}

	return ai, nil
}

// Rename file at the end of processing
func renameFile(filePath string) {
	dirPath, fileName := filepath.Split(filePath)
	newFilePath := dirPath + "." + fileName
	os.Rename(filePath, newFilePath)
}
