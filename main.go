package main

import (
    "encoding/base64"
    "encoding/json"
    "fmt"
    "io/ioutil"
    "net/http"
    "os"
    "os/exec"
    "sync"
    "time"

    "github.com/gin-contrib/cors"
    "github.com/gin-gonic/gin"
)

type Layer struct {
    Title  string `json:"title"`
    Canvas string `json:"canvas"`
}

type ProcessRequest struct {
    Layers []Layer `json:"layers"`
}

func processLayer(layer Layer, wg *sync.WaitGroup, results chan<- string) {
    defer wg.Done()

    data, err := base64.StdEncoding.DecodeString(layer.Canvas)
    if err != nil {
        results <- fmt.Sprintf("Error decoding image for %s: %v", layer.Title, err)
        return
    }

    tmpfile, err := ioutil.TempFile("", "canvas-*.png")
    if err != nil {
        results <- fmt.Sprintf("Error creating temp file for %s: %v", layer.Title, err)
        return
    }
    defer os.Remove(tmpfile.Name())
    if _, err := tmpfile.Write(data); err != nil {
        results <- fmt.Sprintf("Error writing to temp file for %s: %v", layer.Title, err)
        return
    }
    tmpfile.Close()

    cmd := exec.Command("python3", "process_image.py", tmpfile.Name(), layer.Title)
    output, err := cmd.CombinedOutput()
    if err != nil {
        results <- fmt.Sprintf("Python error for %s: %v, output: %s", layer.Title, err, output)
        return
    }

    results <- fmt.Sprintf("Result for %s: %s", layer.Title, output)
}

func main() {
    r := gin.Default()
    r.Use(cors.New(cors.Config{
        AllowOrigins:     []string{"http://localhost:3000"},
        AllowMethods:     []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"},
        AllowHeaders:     []string{"Origin", "Content-Type", "Authorization"},
        ExposeHeaders:    []string{"Content-Length"},
        AllowCredentials: true,
        MaxAge:           12 * time.Hour,
    }))

    r.GET("/ping", func(c *gin.Context) {
        c.JSON(http.StatusOK, gin.H{"message": "pong"})
    })

    r.POST("/process", func(c *gin.Context) {
        var req ProcessRequest
        if err := c.ShouldBindJSON(&req); err != nil {
            c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
            return
        }

        var wg sync.WaitGroup
        results := make(chan string, len(req.Layers))
        for _, layer := range req.Layers {
            wg.Add(1)
            go processLayer(layer, &wg, results)
        }
        wg.Wait()
        close(results)

        var output []string
        for res := range results {
            output = append(output, res)
        }

        c.JSON(http.StatusOK, gin.H{
            "status": "Processed layers concurrently",
            "results": output,
        })
    })

    r.Run(":8080")
}