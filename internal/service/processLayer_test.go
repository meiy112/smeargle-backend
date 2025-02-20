package service

import (
	"encoding/base64"
	"io/ioutil"
	"log"
	"sync"
	"testing"
)

func TestProcessLayer(t *testing.T) {
	imgData, err := ioutil.ReadFile("images/smeargle.jpg")
	if err != nil {
		log.Fatalf("Error reading image file: %v", err)
	}

	sampleBase64 := base64.StdEncoding.EncodeToString(imgData)

	sampleLayer := Layer{
		Title:  "Box",
		Canvas: sampleBase64,
	}

	var wg sync.WaitGroup
	results := make(chan string, 1)

	wg.Add(1)
	go ProcessLayer(sampleLayer, &wg, results)
	wg.Wait()
	close(results)

	var output string
	for res := range results {
		output = res
	}

	if output == "" {
		t.Error("Expected output from processLayer, got empty string")
	} else {
		t.Logf("processLayer output: %s", output)
	}
}
