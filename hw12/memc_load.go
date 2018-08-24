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
	"sync"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
)

const (
	ChannelSize   = 100
	NormalErrRate = 0.01
)

type MemcachedClient struct {
	addr   string
	client memcache.Client
	ch     chan *MemcacheUnit
}

type AppsInstalled struct {
	devType string
	devId   string
	lat     float64
	lon     float64
	apps    []uint32
}

type MemcacheUnit struct {
	key string
	data []byte
	filePath string
}

type Stat struct {
	filePath string
	processed int
	errors int
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

	filePaths, err := filepath.Glob(*filesPattern)
	if err != nil || len(filePaths) < 1 {
		log.Fatalf("Files by pattern %v not found. Exit", *filesPattern)
		return
	}

	// Create and run memcached clients workers
	statCh := make(chan Stat, ChannelSize)
	memcClients := createMemcachedClientsMap(*idfa, *gaid, *adid, *dvid)

	for _, memcCl := range memcClients {
		go memcCl.worker(statCh, filePaths, *isDry)
	}

	var wgr sync.WaitGroup
	for _, filePath := range filePaths {
		wgr.Add(1)
		go processFileWorker(filePath, memcClients, statCh, &wgr)
	}
	wgr.Wait()

	// Send sentinel flag to MemcachedClient workers
	for _, memCl := range memcClients {
		memCl.ch <- nil
	}

	// Got stat from stat channel and write to log
	getAndLogStat(filePaths, memcClients, statCh)
}

/* ================
Worker funcs
================ */

// Read file line by line
// Parse each line to AppsInstalled struct and send it to MemcachedClient
func processFileWorker(filePath string, memcClients map[string]MemcachedClient, statCh chan Stat, wgr *sync.WaitGroup) {
	log.Printf("%v: start processing", filePath)

	fileStat := Stat{
		errors:0,
		processed:0,
		filePath:filePath,
	}
	defer func(statCh chan Stat, fileStat Stat){
		log.Printf("%v ready", filePath)
		statCh <- fileStat
		wgr.Done()
		renameFile(filePath)
	}(statCh, fileStat)

	// Run goroutine for counting errors from other goroutines-workers
	file, err := os.Open(filePath)
	if err != nil {
		log.Fatalf("Can't open file: %v", err)
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
	// Every success parsed line send to according MemcachedClient
	scanner := bufio.NewScanner(gz)
	for scanner.Scan() {
		fileStat.processed += 1

		line := scanner.Text()
		if len(line) < 1 {
			continue
		}

		ai, err := parseLine(line)
		if err != nil {
			fileStat.errors += 1
			continue
		}

		memcCl, ok := memcClients[ai.devType]
		if !ok {
			fileStat.errors += 1
			log.Printf("Unknown device type: %v", ai.devType)
			continue
		}

		ua := &appsinstalled.UserApps{
			Lat:  proto.Float64(ai.lat),
			Lon:  proto.Float64(ai.lon),
			Apps: ai.apps,
		}
		packed, err := proto.Marshal(ua)
		if err != nil {
			fileStat.errors += 1
			continue
		}

		mu := MemcacheUnit{
			key:fmt.Sprintf("%s:%s", ai.devType, ai.devId),
			data:packed,
			filePath:filePath,
		}

		memcCl.ch <- &mu

		if fileStat.processed%1000000 == 0 {
			log.Printf("%v: ready %v lines", filePath, fileStat.processed)
		}
	}
}

// MemcachedClient worker - read AppsInstalled structs
// from channel and send to according memcached
// Count errors by files
func (mc MemcachedClient) worker(statCh chan Stat, filePaths []string, dry bool) {
	log.Printf("%v started", mc.addr)

	filesStatMap := createStatMap(filePaths)
	defer func(statCh chan Stat, filesStat map[string]*Stat) {
		log.Printf("%v - got SentinelFlag", mc.addr)
		for _, statMap := range filesStat {
			statCh <- *statMap
		}
	}(statCh, filesStatMap)

	var readyLines int
	for {
		mu := <-mc.ch

		if mu == nil {
			break
		}

		if dry {
			readyLines += 1
			if readyLines % 100000 == 0 {
				log.Printf("%v: ready %v lines", mc.addr, readyLines)
			}
			filesStatMap[mu.filePath].processed += 1
		} else {
			err := mc.client.Set(&memcache.Item{
				Key:   mu.key,
				Value: mu.data,
			})
			if err != nil {
				filesStatMap[mu.filePath].errors += 1
				log.Fatalf("Can't set %v to memc: %v", mu.key, mc.addr)
			}
		}
	}
}

/* ================
Create funcs
================ */

func createMemcachedClientsMap(idfa, gaid, adid, dvid string) map[string]MemcachedClient {
	memcClients := make(map[string]MemcachedClient)
	memcClients["idfa"] = MemcachedClient{
		idfa,
		*memcache.New(idfa),
		make(chan *MemcacheUnit, ChannelSize),
	}
	memcClients["gaid"] = MemcachedClient{
		gaid,
		*memcache.New(gaid),
		make(chan *MemcacheUnit, ChannelSize),
	}
	memcClients["adid"] = MemcachedClient{
		adid,
		*memcache.New(adid),
		make(chan *MemcacheUnit, ChannelSize),
	}
	memcClients["dvid"] = MemcachedClient{
		dvid,
		*memcache.New(dvid),
		make(chan *MemcacheUnit, ChannelSize),
	}

	return memcClients
}

/* ================
Stat logging funcs
================ */

func createStatMap(filePaths []string) map[string]*Stat {
	filesStatMap := make(map[string]*Stat)
	for _, filePath := range filePaths {
		filesStatMap[filePath] = &Stat{
			filePath:filePath,
			processed:0,
			errors:0,
		}
	}

	return filesStatMap
}

// Receive stat by files from channels of workers and log it
func getAndLogStat(filePaths []string, memcClients map[string]MemcachedClient, statCh chan Stat) {
	filesStatMap := createStatMap(filePaths)
	totalStat := Stat{
		processed:0,
		errors:0,
		filePath:"Total",
	}
	for i:=0; i<(len(memcClients)+len(filePaths)); i++ {
		fileStat := <-statCh

		filesStatMap[fileStat.filePath].processed += fileStat.processed
		filesStatMap[fileStat.filePath].errors += fileStat.errors

		totalStat.processed += fileStat.processed
		totalStat.errors += fileStat.errors
	}

	for _, fileStat := range filesStatMap {
		logFileStat(*fileStat)
	}
	logFileStat(totalStat)
}

func logFileStat(fileStat Stat) {
	if fileStat.processed > 0 {
		errRate := float64(fileStat.errors) / float64(fileStat.processed)
		if errRate <= NormalErrRate {
			log.Printf(
				"%v: Success. Error rate %v/%v = %v",
				fileStat.filePath,
				fileStat.errors,
				fileStat.processed,
				errRate,
			)
		} else {
			log.Fatalf(
				"%v: Fail. Error rate %v/%v = %v",
				fileStat.filePath,
				fileStat.errors,
				fileStat.processed,
				errRate,
			)
		}
	}
}

/* ================
Other funcs
================ */

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
