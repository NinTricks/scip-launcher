BINARY = lanzador
SRC = lanzador.go

.PHONY: all build clean

all: build

build:
	go build -o $(BINARY) $(SRC)

clean:
	rm -f $(BINARY) resumen_*.txt
clean_logs:
	rm problemas/*.log
