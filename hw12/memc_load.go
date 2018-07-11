package main

import (
	"flag"
	"golang.org/x/sync/semaphore"
	"log"
	"os"
	"path/filepath"
	"sync"
	"bufio"
	"sync/atomic"
	"time"
	"strings"
	"errors"
	"strconv"
	"compress/gzip"
)

const (
	MaxActiveGoroutines = 1000
	MaxMemcConns        = 10
	Tries               = 3
	DelayMS             = 1
	BackoffMult         = 2
	NormalErrRate		= 0.01
)

type CommandArgs struct {
	test         bool
	logPath      string
	filesPattern string

	idfa string
	gaid string
	adid string
	dvid string
}

type MemcachedClient struct {
	addr string
	sem  semaphore.Weighted
}

type AppsInstalled struct {
	devType string
	devId   string
	lat     float64
	lon     float64
	apps    []int
}

func main() {
	comArgs := parseArgs()

	logfile, _ := os.Create(comArgs.logPath)
	logObj := log.New(logfile, "", 0)

	if comArgs.test {
		testParser(*logObj)
		return
	}

	memcClients := createMemcachedClientsMap(comArgs)

	files, err := filepath.Glob(comArgs.filesPattern)
	if err != nil || len(files) < 1 {
		logObj.Fatalf("Files by pattern %v not found. Exit", comArgs.filesPattern)
		return
	}

	for _, filePath := range files {
		processFile(filePath, memcClients, *logObj)
	}
}

// Test parser of AppsInstalled from line
// TODO: Realize it
func testParser(logObj log.Logger) {
	logObj.Print("test")
}

func createMemcachedClientsMap(comArgs CommandArgs) map[string]MemcachedClient {
	memcClients := make(map[string]MemcachedClient)
	memcClients["idfa"] = MemcachedClient{
		comArgs.idfa,
		*semaphore.NewWeighted(int64(MaxMemcConns)),
	}
	memcClients["gaid"] = MemcachedClient{
		comArgs.gaid,
		*semaphore.NewWeighted(int64(MaxMemcConns)),
	}
	memcClients["adid"] = MemcachedClient{
		comArgs.adid,
		*semaphore.NewWeighted(int64(MaxMemcConns)),
	}
	memcClients["dvid"] = MemcachedClient{
		comArgs.dvid,
		*semaphore.NewWeighted(int64(MaxMemcConns)),
	}

	return memcClients
}

func parseArgs() CommandArgs {
	test := flag.Bool("test", false, "test parser")
	logPath := flag.String("log", "./memc.log", "path to log file")
	filesPattern := flag.String("pattern", "/data/appsinstalled/*.tsv.gz", "files path pattern")

	idfa := flag.String("idfa", "127.0.0.1:33013", "ip and port of idfa memcached server")
	gaid := flag.String("gaid", "127.0.0.1:33014", "ip and port of gaid memcached server")
	adid := flag.String("adid", "127.0.0.1:33015", "ip and port of adid memcached server")
	dvid := flag.String("dvid", "127.0.0.1:33016", "ip and port of dvid memcached server")

	flag.Parse()

	comArgs := CommandArgs{
		*test,
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
func processFile(filePath string, memcClients map[string]MemcachedClient, logObj log.Logger) {
	logObj.Printf("%v: start processing", filePath)

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

		ai, err := parseLine(line, logObj)
		if err != nil {
			errorsCount += 1
			continue
		}

		memcClient, ok := memcClients[ai.devType]
		if !ok {
			errorsCount += 1
			logObj.Printf("Unknown device type: %v", ai.devType)
			continue
		}

		for {
			activeGoroutinesNow := atomic.LoadUint32(&activeGoroutines)
			if activeGoroutinesNow < MaxActiveGoroutines {
				break
			}
			time.Sleep(100 * time.Millisecond)
		}
		go memcClient.updateMemcache(ai, &activeGoroutines)

		processed += 1
		if processed % 10000 == 0 {
			logObj.Printf("%v: ready %v lines", filePath, processed)
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
			logObj.Printf("%v: Success. Error rate (%v)", filePath, errRate)
		} else {
			logObj.Fatalf("%v: Fail. Error rate (%v)", filePath, errRate)
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
// TODO: Realize it
func (mc *MemcachedClient) updateMemcache(ai AppsInstalled, activeGr *uint32) {
	atomic.AddUint32(activeGr, 1)
	defer atomic.AddUint32(activeGr, ^uint32(0))

}

// Parse line from file to AppsInstalled struct
// Return error if can't parse line
func parseLine(line string, logObj log.Logger) (AppsInstalled, error) {
	var ai AppsInstalled

	lineParts := strings.Split(strings.TrimSpace(line), "\t")

	if len(lineParts) < 5 {
		return ai, errors.New("malformed line")
	}
	if len(lineParts[0]) == 0 || len(lineParts[1]) == 0 {
		return ai, errors.New("malformed line")
	}

	appsStrSlice := strings.Split(lineParts[4], ",")
	var appsIntSlice []int
	var hasError bool
	for _, appStr := range appsStrSlice {
		appInt, err := strconv.Atoi(appStr)
		if err != nil {
			hasError = true
		} else {
			appsIntSlice = append(appsIntSlice, appInt)
		}
	}
	if hasError {
		logObj.Fatalf("Not all user apps are digits: %v", line)
	}

	lat, err := strconv.ParseFloat(lineParts[2], 64)
	lon, err := strconv.ParseFloat(lineParts[3], 64)
	if err != nil {
		logObj.Fatalf("Invalid geo coords: %v", line)
	}

	ai = AppsInstalled{
		devType: lineParts[0],
		devId: lineParts[1],
		apps: appsIntSlice,
		lat: lat,
		lon: lon,
	}

	return ai, nil
}

// Rename file at the end of processing
func renameFile(filePath string) {
	dirPath, fileName := filepath.Split(filePath)
	newFilePath := dirPath + "." + fileName
	os.Rename(filePath, newFilePath)
}
