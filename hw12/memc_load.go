package main

import (
	"./appsinstalled"
	"bufio"
	"compress/gzip"
	"errors"
	"flag"
	"fmt"
	"github.com/bradfitz/gomemcache/memcache"
	"github.com/golang/protobuf/proto"
	"log"
	"os"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
)

const (
	ChannelSize   = 100
	NormalErrRate = 0.01
	SentinelFlag  = -1
)

type MemcachedClient struct {
	addr   string
	client memcache.Client
	ch     chan *AppsInstalled
}

type AppsInstalled struct {
	devType string
	devId   string
	lat     float64
	lon     float64
	apps    []uint32
}

func main() {
	isTest := flag.Bool("test", false, "test protobuf")
	isDry := flag.Bool("dry", false, "debug mode (without sending to memcached)")
	logPath := flag.String("log", "./memc.log", "path to log file")
	filesPattern := flag.String("pattern", "/data/appsinstalled/*.tsv.gz", "files path pattern")

	idfa := flag.String("idfa", "127.0.0.1:33013", "ip and port of idfa memcached server")
	gaid := flag.String("gaid", "127.0.0.1:33014", "ip and port of gaid memcached server")
	adid := flag.String("adid", "127.0.0.1:33015", "ip and port of adid memcached server")
	dvid := flag.String("dvid", "127.0.0.1:33016", "ip and port of dvid memcached server")

	flag.Parse()

	if *isTest {
		prototest()
		return
	}

	logfile, err := os.OpenFile(*logPath, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0644)
	if err != nil {
		log.Fatalf("Cannot open log file: %s", *logPath)
		return
	}
	log.SetOutput(logfile)
	defer logfile.Close()

	memcClients := createMemcachedClientsMap(*idfa, *gaid, *adid, *dvid)

	files, err := filepath.Glob(*filesPattern)
	if err != nil || len(files) < 1 {
		log.Fatalf("Files by pattern %v not found. Exit", *filesPattern)
		return
	}

	for _, filePath := range files {
		processFile(filePath, memcClients, *isDry)
	}

	// Close memcachedClient's channels
	for _, memCl := range memcClients {
		close(memCl.ch)
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

func createMemcachedClientsMap(idfa, gaid, adid, dvid string) map[string]MemcachedClient {
	memcClients := make(map[string]MemcachedClient)
	memcClients["idfa"] = MemcachedClient{
		idfa,
		*memcache.New(idfa),
		make(chan *AppsInstalled, ChannelSize),
	}
	memcClients["gaid"] = MemcachedClient{
		gaid,
		*memcache.New(gaid),
		make(chan *AppsInstalled, ChannelSize),
	}
	memcClients["adid"] = MemcachedClient{
		adid,
		*memcache.New(adid),
		make(chan *AppsInstalled, ChannelSize),
	}
	memcClients["dvid"] = MemcachedClient{
		dvid,
		*memcache.New(dvid),
		make(chan *AppsInstalled, ChannelSize),
	}

	return memcClients
}

// Read file line by line
// Parse each line to AppsInstalled struct and send it to MemcachedClient
// Count errors from goroutines in separate goroutine
func processFile(filePath string, memcClients map[string]MemcachedClient, dry bool) {
	log.Printf("%v: start processing", filePath)

	processed, errorsCount := 0, 0

	// Run goroutine for counting errors from other goroutines-workers
	errorsCh := make(chan int)
	errorsResultCh := make(chan int)
	go countErrorsWorker(errorsCh, errorsResultCh, len(memcClients))

	// Run memcached clients workers
	for clName, memcCl := range memcClients {
		log.Printf("%v - start worker", clName)
		go memcCl.worker(errorsCh, dry)
	}

	file, err := os.Open(filePath)
	if err != nil {
		log.Fatalf("Can't open file: %v", err)
		for _, memcCl := range memcClients {
			memcCl.ch <- nil
		}
		return
	}
	defer file.Close()

	gz, err := gzip.NewReader(file)
	if err != nil {
		log.Printf("Can't create a new Reader %v", err)
		for _, memcCl := range memcClients {
			memcCl.ch <- nil
		}
		return
	}
	defer gz.Close()

	// Read file and parse every line in loop.
	// Every success parsed line send to according MemcachedClient
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

		memcCl, ok := memcClients[ai.devType]
		if !ok {
			errorsCount += 1
			log.Printf("Unknown device type: %v", ai.devType)
			continue
		}

		memcCl.ch <- &ai

		processed += 1
		if processed%1000000 == 0 {
			log.Printf("%v: ready %v lines", filePath, processed)
		}
	}

	for _, memcCl := range memcClients {
		memcCl.ch <- nil
	}

	errCount := <-errorsResultCh
	processed -= errCount
	errorsCount += errCount

	if processed > 0 {
		errRate := float64(errorsCount) / float64(processed)
		if errRate <= NormalErrRate {
			log.Printf("%v: Success. Error rate %v/%v = %v", filePath, errorsCount, processed, errRate)
		} else {
			log.Fatalf("%v: Fail. Error rate %v/%v = %v", filePath, errorsCount, processed, errRate)
		}
	}
	renameFile(filePath)
}

// Count errors from MemcachedClient workers
// Exit, when receive N SentinelFlags, where N == workersCount
func countErrorsWorker(errorsCh, errorsResultCh chan int, workersCount int) {
	var errorsCount int
	var workersCompleted int

	for {
		err := <-errorsCh
		if err > 0 {
			errorsCount += err
		} else if err == SentinelFlag {
			workersCompleted += 1
			if workersCompleted == workersCount {
				log.Printf("Completed all workers")
				errorsResultCh <- errorsCount
				return
			}
		} else {
			log.Fatalf("Unknown code in errorsCh channel: %v", err)
			errorsCh <- errorsCount
			return
		}
	}
}

// MemcachedClient worker - read AppsInstalled structs
// from channel and send to according memcached
func (mc MemcachedClient) worker(errorsCh chan int, dry bool) {
	var readyLines int
	log.Printf("%v started", mc.addr)
	for {
		ai := <-mc.ch
		if ai == nil {
			errorsCh <- SentinelFlag
			log.Printf("%v - got SentinelFlag", mc.addr)
			break
		}

		ua := &appsinstalled.UserApps{
			Lat:  proto.Float64(ai.lat),
			Lon:  proto.Float64(ai.lon),
			Apps: ai.apps,
		}
		key := fmt.Sprintf("%s:%s", ai.devType, ai.devId)
		packed, _ := proto.Marshal(ua)

		if dry {
			readyLines += 1
			if readyLines%250000 == 0 {
				errorsCh <- 1
				log.Printf("%v - ready %v lines", mc.addr, readyLines)
			}
		} else {
			err := mc.client.Set(&memcache.Item{
				Key:   key,
				Value: packed,
			})
			if err != nil {
				log.Fatalf("Can't set %s to memc: %s", key, mc.addr)
				errorsCh <- 1
			}
		}
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
