package main

import (
	"fmt"
	"log"
	"net/http"
)

func main() {
	// Serve static files from current directory
	fs := http.FileServer(http.Dir("."))
	http.Handle("/", fs)

	fmt.Println("Mining pool server starting on http://127.0.0.1:8080")
	log.Fatal(http.ListenAndServe("127.0.0.1:8080", nil))
}
