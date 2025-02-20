package main

import (
	"net/http"
	"sync"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/meiy112/smeargle-backend/internal/service"
)

type Layer struct {
	Title  string
	Canvas string
}

type ProcessRequest struct {
	Layers []Layer `json:"layers"`
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
			go service.ProcessLayer(service.Layer{Title: layer.Title, Canvas: layer.Canvas}, &wg, results)
		}
		wg.Wait()
		close(results)

		var output []string
		for res := range results {
			output = append(output, res)
		}

		c.JSON(http.StatusOK, gin.H{
			"status":  "Processed layers concurrently",
			"results": output,
		})
	})

	r.Run(":8080")
}
