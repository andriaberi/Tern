CFLAGS   := -std=c11 -Wall -Wextra -Wpedantic -Werror -g
CPPFLAGS := -Iinclude -MMD -MP

BUILD := build
SRCS  := $(wildcard src/*.c)
OBJS  := $(SRCS:src/%.c=$(BUILD)/obj/%.o)
BIN   := $(BUILD)/tern

SANITIZE := -fsanitize=address,undefined -fno-omit-frame-pointer

.PHONY: all test asan clean

all: $(BIN)

$(BIN): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $^

$(BUILD)/obj/%.o: src/%.c | $(BUILD)/obj
	$(CC) $(CPPFLAGS) $(CFLAGS) -c -o $@ $<

$(BUILD)/obj:
	mkdir -p $@

test: $(BIN)
	python3 tests/run_tests.py --compiler $(BIN)

# Build with AddressSanitizer + UBSan into build/asan and run the test suite.
asan:
	$(MAKE) BUILD=build/asan CFLAGS="$(CFLAGS) $(SANITIZE)" test

clean:
	rm -rf build

-include $(OBJS:.o=.d)
