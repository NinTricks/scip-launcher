BINARY = lanzador
SRC = lanzador3.go

.PHONY: all build clean

all: build

build:
	go build -o $(BINARY) $(SRC)

clean:
	rm -f $(BINARY) resumen_*.txt
