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

# Runtime profiles keep each hardware image inside SpiNNaker per-core memory
# budgets. The default remains the full runtime for host tests and legacy
# probes; tiny native mechanism gates can request a smaller profile.
RUNTIME_PROFILE ?= full

# 4.27e: Enable MCPL inter-core lookup (multicast payload) instead of SDP.
# Set USE_MCPL_LOOKUP=1 when building distributed profiles.
USE_MCPL_LOOKUP ?= 0
ifeq ($(USE_MCPL_LOOKUP),1)
MCPL_CFLAGS := -DCRA_USE_MCPL_LOOKUP=1
else
MCPL_CFLAGS :=
endif

FULL_RUNTIME_SOURCES := \
	src/neuron_manager.c \
	src/synapse_manager.c \
	src/state_manager.c \
	src/host_interface.c \
	src/router.c

ifeq ($(RUNTIME_PROFILE),full)
RUNTIME_SOURCES := $(FULL_RUNTIME_SOURCES)
RUNTIME_PROFILE_CFLAGS := -DCRA_RUNTIME_PROFILE_FULL=1 -DRUNTIME_PROFILE_ID=0
else ifeq ($(RUNTIME_PROFILE),decoupled_memory_route)
RUNTIME_SOURCES := \
	src/state_manager.c \
	src/host_interface.c
RUNTIME_PROFILE_CFLAGS := -DCRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE=1 -DRUNTIME_PROFILE_ID=1
else ifeq ($(RUNTIME_PROFILE),state_core)
RUNTIME_SOURCES := \
	src/state_manager.c \
	src/host_interface.c
RUNTIME_PROFILE_CFLAGS := -DCRA_RUNTIME_PROFILE_STATE_CORE=1 -DCRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE=1 -DRUNTIME_PROFILE_ID=2
else ifeq ($(RUNTIME_PROFILE),learning_core)
RUNTIME_SOURCES := \
	src/state_manager.c \
	src/host_interface.c
RUNTIME_PROFILE_CFLAGS := -DCRA_RUNTIME_PROFILE_LEARNING_CORE=1 -DCRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE=1 -DRUNTIME_PROFILE_ID=3
else ifeq ($(RUNTIME_PROFILE),context_core)
RUNTIME_SOURCES := \
	src/state_manager.c \
	src/host_interface.c
RUNTIME_PROFILE_CFLAGS := -DCRA_RUNTIME_PROFILE_CONTEXT_CORE=1 -DCRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE=1 -DRUNTIME_PROFILE_ID=4
else ifeq ($(RUNTIME_PROFILE),route_core)
RUNTIME_SOURCES := \
	src/state_manager.c \
	src/host_interface.c
RUNTIME_PROFILE_CFLAGS := -DCRA_RUNTIME_PROFILE_ROUTE_CORE=1 -DCRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE=1 -DRUNTIME_PROFILE_ID=5
else ifeq ($(RUNTIME_PROFILE),memory_core)
RUNTIME_SOURCES := \
	src/state_manager.c \
	src/host_interface.c
RUNTIME_PROFILE_CFLAGS := -DCRA_RUNTIME_PROFILE_MEMORY_CORE=1 -DCRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE=1 -DRUNTIME_PROFILE_ID=6
else
$(error Unsupported RUNTIME_PROFILE '$(RUNTIME_PROFILE)'; expected full, decoupled_memory_route, state_core, learning_core, context_core, route_core, or memory_core)
endif

HARDWARE_SOURCES := src/main.c $(RUNTIME_SOURCES)
APP_OUTPUT_DIR := build/
BUILD_DIR := build/gnu/

HOST_TEST := tests/test_runtime
HOST_TEST_SOURCES := tests/test_runtime.c stubs/spin1_api.c $(FULL_RUNTIME_SOURCES)
HOST_CC ?= cc
HOST_CFLAGS ?= -std=c11 -Wall -Wextra -Wno-unused-parameter -Wno-int-to-pointer-cast -I stubs -I src
HOST_LDFLAGS ?= -lm

# ------------------------------------------------------------------------------
# Host-side tests
# ------------------------------------------------------------------------------

.PHONY: test host-test test-profiles test-four-core-local test-four-core-48event test-context-core test-route-core test-memory-core test-learning-core test-mcpl-feasibility
test host-test: $(HOST_TEST)
	./$(HOST_TEST)

test-profiles: test-context-core test-route-core test-memory-core test-learning-core

PROFILE_TEST_SOURCES := tests/test_profiles.c stubs/spin1_api.c src/state_manager.c src/host_interface.c

test-context-core: $(PROFILE_TEST_SOURCES) src/config.h stubs/sark.h stubs/spin1_api.h
	$(HOST_CC) $(HOST_CFLAGS) -DCRA_RUNTIME_PROFILE_CONTEXT_CORE=1 -DCRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE=1 -DRUNTIME_PROFILE_ID=4 $(PROFILE_TEST_SOURCES) $(HOST_LDFLAGS) -o tests/test_context_core
	./tests/test_context_core

test-route-core: $(PROFILE_TEST_SOURCES) src/config.h stubs/sark.h stubs/spin1_api.h
	$(HOST_CC) $(HOST_CFLAGS) -DCRA_RUNTIME_PROFILE_ROUTE_CORE=1 -DCRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE=1 -DRUNTIME_PROFILE_ID=5 $(PROFILE_TEST_SOURCES) $(HOST_LDFLAGS) -o tests/test_route_core
	./tests/test_route_core

test-memory-core: $(PROFILE_TEST_SOURCES) src/config.h stubs/sark.h stubs/spin1_api.h
	$(HOST_CC) $(HOST_CFLAGS) -DCRA_RUNTIME_PROFILE_MEMORY_CORE=1 -DCRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE=1 -DRUNTIME_PROFILE_ID=6 $(PROFILE_TEST_SOURCES) $(HOST_LDFLAGS) -o tests/test_memory_core
	./tests/test_memory_core

test-learning-core: $(PROFILE_TEST_SOURCES) src/config.h stubs/sark.h stubs/spin1_api.h
	$(HOST_CC) $(HOST_CFLAGS) -DCRA_RUNTIME_PROFILE_LEARNING_CORE=1 -DCRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE=1 -DRUNTIME_PROFILE_ID=3 $(PROFILE_TEST_SOURCES) $(HOST_LDFLAGS) -o tests/test_learning_core
	./tests/test_learning_core

FOUR_CORE_TEST_SOURCES := tests/test_four_core_local.c stubs/spin1_api.c src/state_manager.c src/host_interface.c

test-four-core-local: $(FOUR_CORE_TEST_SOURCES) src/config.h stubs/sark.h stubs/spin1_api.h
	$(HOST_CC) $(HOST_CFLAGS) -DCRA_RUNTIME_PROFILE_LEARNING_CORE=1 -DCRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE=1 -DRUNTIME_PROFILE_ID=3 $(FOUR_CORE_TEST_SOURCES) $(HOST_LDFLAGS) -o tests/test_four_core_local
	./tests/test_four_core_local

FOUR_CORE_48EVENT_TEST_SOURCES := tests/test_four_core_48event.c stubs/spin1_api.c src/state_manager.c src/host_interface.c

test-four-core-48event: $(FOUR_CORE_48EVENT_TEST_SOURCES) tests/test_four_core_48event_data.h src/config.h stubs/sark.h stubs/spin1_api.h
	$(HOST_CC) $(HOST_CFLAGS) -I tests -DCRA_RUNTIME_PROFILE_LEARNING_CORE=1 -DCRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE=1 -DRUNTIME_PROFILE_ID=3 $(FOUR_CORE_48EVENT_TEST_SOURCES) $(HOST_LDFLAGS) -o tests/test_four_core_48event
	./tests/test_four_core_48event

MCPL_TEST_SOURCES := tests/test_mcpl_feasibility.c stubs/spin1_api.c src/state_manager.c

test-mcpl-feasibility: $(MCPL_TEST_SOURCES) src/config.h stubs/sark.h stubs/spin1_api.h
	$(HOST_CC) $(HOST_CFLAGS) -DCRA_RUNTIME_PROFILE_LEARNING_CORE=1 -DCRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE=1 -DRUNTIME_PROFILE_ID=3 $(MCPL_TEST_SOURCES) $(HOST_LDFLAGS) -o tests/test_mcpl_feasibility
	./tests/test_mcpl_feasibility

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

# The custom runtime is deployed into SpiNNaker's small per-core instruction
# memory, so hardware builds optimize for size. Host tests use HOST_CFLAGS.
CFLAGS += -I src -Os -ffunction-sections -fdata-sections $(RUNTIME_PROFILE_CFLAGS) $(MCPL_CFLAGS)
LDFLAGS += -Wl,--gc-sections

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
	rm -rf $(BUILD_DIR) $(APP_OUTPUT_DIR)$(APP).aplx $(HOST_TEST) tests/test_context_core tests/test_route_core tests/test_memory_core tests/test_learning_core tests/test_four_core_local tests/test_four_core_48event

clean-host:
	rm -f $(HOST_TEST) tests/test_context_core tests/test_route_core tests/test_memory_core tests/test_learning_core tests/test_four_core_local tests/test_four_core_48event

help:
	@printf '%s\n' \
		'Coral Reef SpiNNaker Runtime targets:' \
		'  make test              Build and run host-side tests (no SPINN_DIRS needed)' \
		'  make host-test         Alias for make test' \
		'  make test-profiles     Build and run all four 4.26 profile tests' \
		'  make all               Build hardware .aplx image (requires spinnaker_tools)' \
		'  make hardware          Alias for make all' \
		'  make clean             Remove generated build/test artifacts'
