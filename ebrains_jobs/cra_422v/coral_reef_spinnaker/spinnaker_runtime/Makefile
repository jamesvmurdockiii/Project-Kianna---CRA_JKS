# ------------------------------------------------------------------------------
# Coral Reef SpiNNaker Runtime — Makefile
# ------------------------------------------------------------------------------
#
# Targets:
#   make test       Build and run host-side runtime tests using local C compiler
#   make host-test  Alias for make test
#   make all        Build hardware .aplx image using spinnaker_tools
#   make hardware   Alias for make all
#   make clean      Remove generated build products and host test binary
#
# Host tests use stubs/ and do not require SPINN_DIRS. Hardware targets require
# spinnaker_tools and will explain how to configure it if unavailable.
# ------------------------------------------------------------------------------

APP := coral_reef
.DEFAULT_GOAL := all

RUNTIME_SOURCES := \
	src/neuron_manager.c \
	src/synapse_manager.c \
	src/state_manager.c \
	src/host_interface.c \
	src/router.c

HARDWARE_SOURCES := src/main.c $(RUNTIME_SOURCES)
APP_OUTPUT_DIR := build/
BUILD_DIR := build/gnu/

HOST_TEST := tests/test_runtime
HOST_TEST_SOURCES := tests/test_runtime.c $(RUNTIME_SOURCES)
HOST_CC ?= cc
HOST_CFLAGS ?= -std=c11 -Wall -Wextra -Wno-unused-parameter -Wno-int-to-pointer-cast -I stubs -I src
HOST_LDFLAGS ?= -lm

# ------------------------------------------------------------------------------
# Host-side tests
# ------------------------------------------------------------------------------

.PHONY: test host-test
test host-test: $(HOST_TEST)
	./$(HOST_TEST)

$(HOST_TEST): $(HOST_TEST_SOURCES) src/config.h stubs/sark.h stubs/spin1_api.h
	$(HOST_CC) $(HOST_CFLAGS) $(HOST_TEST_SOURCES) $(HOST_LDFLAGS) -o $@

# ------------------------------------------------------------------------------
# Hardware build configuration
# ------------------------------------------------------------------------------

ifndef SPINN_INSTALL_DIR
ifneq (,$(SPINN_DIRS))
SPINN_INSTALL_DIR := $(SPINN_DIRS)
else ifneq (,$(wildcard /opt/spinnaker_tools/make/spinnaker_tools.mk))
SPINN_INSTALL_DIR := /opt/spinnaker_tools
else ifneq (,$(wildcard /usr/local/spinnaker_tools/make/spinnaker_tools.mk))
SPINN_INSTALL_DIR := /usr/local/spinnaker_tools
else ifneq (,$(wildcard $(HOME)/spinnaker_tools/make/spinnaker_tools.mk))
SPINN_INSTALL_DIR := $(HOME)/spinnaker_tools
else ifneq (,$(wildcard $(HOME)/spinnaker/spinnaker_tools/make/spinnaker_tools.mk))
SPINN_INSTALL_DIR := $(HOME)/spinnaker/spinnaker_tools
endif
endif

HAVE_SPINNAKER_TOOLS := $(if $(wildcard $(SPINN_INSTALL_DIR)/make/spinnaker_tools.mk),1,0)

ifeq ($(HAVE_SPINNAKER_TOOLS),1)
OBJECTS := $(patsubst %.c,$(BUILD_DIR)%.o,$(HARDWARE_SOURCES))
OBJECT_DIRS := $(sort $(dir $(OBJECTS)))
include $(SPINN_INSTALL_DIR)/make/spinnaker_tools.mk

$(OBJECTS): | $(OBJECT_DIRS)

$(OBJECT_DIRS):
	mkdir -p $@
endif

CFLAGS += -I src

.PHONY: all hardware aplx require-spinnaker
ifeq ($(HAVE_SPINNAKER_TOOLS),1)
all hardware aplx: require-spinnaker $(APP_OUTPUT_DIR)$(APP).aplx
else
all hardware aplx: require-spinnaker $(BUILD_DIR)/$(APP).aplx
endif

require-spinnaker:
	@if [ "$(HAVE_SPINNAKER_TOOLS)" != "1" ]; then \
		printf '%s\n' "spinnaker_tools not found."; \
		printf '%s\n' "Host tests work with 'make test'."; \
		printf '%s\n' "For hardware builds set SPINN_DIRS, e.g.:"; \
		printf '%s\n' "  export SPINN_DIRS=/opt/spinnaker_tools"; \
		exit 2; \
	fi

# ------------------------------------------------------------------------------
# Utility targets
# ------------------------------------------------------------------------------

.PHONY: clean clean-host help
clean:
	rm -rf $(BUILD_DIR) $(HOST_TEST)

clean-host:
	rm -f $(HOST_TEST)

help:
	@printf '%s\n' \
		'Coral Reef SpiNNaker Runtime targets:' \
		'  make test       Build and run host-side tests (no SPINN_DIRS needed)' \
		'  make host-test  Alias for make test' \
		'  make all        Build hardware .aplx image (requires spinnaker_tools)' \
		'  make hardware   Alias for make all' \
		'  make clean      Remove generated build/test artifacts'
