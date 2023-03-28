<template>
  <div class="container-sm">
    <header class="mb-3">
      <h1>BRTX Status</h1>
    </header>

    <main>
      <div
        v-for="status in sortedStatuses"
        :key="status.host"
        class="d-flex m-4"
      >
        <div>
          <div class="d-flex">
            <div class="me-2">
              <i
                class="bi"
                :class="{
                  'bi-check-circle-fill':
                    !status.unavailable && status.isRecent,
                  'bi-circle-fill': !status.unavailable && !status.isRecent,
                  'bi-question-circle-fill': status.unavailable,
                  'text-success': !status.unavailable,
                  'text-warning': status.unavailable,
                }"
                :title="`Updated ${Math.floor(status.age)} seconds ago`"
              ></i>
            </div>
            <div>
              <strong>
                {{ status.host }}
              </strong>
            </div>
          </div>
          <ul class="list-unstyled text-end">
            <li
              v-for="partition in status.partitions"
              :key="partition"
              class="text-muted small"
            >
              {{ partition }}
            </li>
          </ul>
        </div>
        <div class="border-start ms-3 ps-3">
          <div class="d-flex">
            <div class="me-2">GPU</div>
            <div
              v-for="(gpu, i) in status.gpus"
              :key="i"
              class="me-1"
            >
              <meter
                min="0"
                max="100"
                high="67"
                :value="gpu.memoryUsedPercent"
                :title="`GPU ${i} memory: ${gpu.memoryUsedDescription}`"
              >
                GPU {{ i }} memory: {{ gpu.memoryUsedDescription }}
              </meter>
            </div>
          </div>
          <div class="d-flex">
            <div class="me-2">Load</div>
            <div>
              <meter
                min="0"
                max="100"
                high="67"
                :value="status.load.loadPercent"
                :title="`Load: ${status.load.loadDescription}`"
              >
                Load: {{ status.load.loadDescription }}
              </meter>
            </div>
          </div>
          <div class="d-flex">
            <div class="me-2">Mem</div>
            <div>
              <meter
                min="0"
                max="100"
                high="67"
                :value="status.memory.memoryUsedPercent"
                :title="`Main memory: ${status.memory.memoryUsedDescription}`"
              >
                Main memory: {{ status.memory.memoryUsedDescription }}
              </meter>
            </div>
          </div>
          <div class="d-flex">
            <div class="me-2">Disk</div>
            <div
              v-for="disk in status.disks"
              :key="disk.mountpoint"
              class="me-1"
            >
              <meter
                min="0"
                max="100"
                high="67"
                :value="disk.storageUsedPercent"
                :title="`${disk.mountpoint}: ${disk.storageUsedDescription}`"
              >
                {{ disk.mountpoint }}: {{ disk.storageUsedDescription }}
              </meter>
            </div>
          </div>
        </div>
      </div>
    </main>

    <footer class="mt-3">
      <p class="text-muted">
        Last update:
        {{ lastUpdateDatetime ? lastUpdateDatetime.toLocaleString() : "None" }}.
        Updated about once per minute.
        <a href="https://github.com/ccmaymay/brtx-status/issues/new">
          Report an issue
        </a>
      </p>
    </footer>
  </div>
</template>

<script>
import axios from "axios";
import { last, sortBy } from "lodash";

// Mark node as unavailable at 5 * 60 seconds
const AGE_UNAVAILABLE = 5 * 60;

// Mark update as recent when within last 3 seconds
const RECENTNESS_THRESHOLD = 3;

// Attempt to retrieve new status every 60 seconds
const RETRIEVAL_RATE = 60;

// Names of nodes (hosts) to show
const NODES = [601, 602, 603, 604, 605, 606].map((i) => `brtx${i}`);

function setAge(st) {
  // Mark as unavailable if either:
  // 1. We weren't able to retrieve status from the server recently or
  // 2. The retrieved status does not have a recent timestamp
  const clientAge = (new Date() - st.retrievedDatetime) / 1000;
  const serverAge = (new Date() - st.datetime) / 1000;
  st.unavailable = clientAge >= AGE_UNAVAILABLE || serverAge >= AGE_UNAVAILABLE;

  // Update status based on availability
  if (st.unavailable) {
    st.gpus.forEach(function (gpu) {
      gpu.utilizationPercent = 0;
      gpu.memoryUsedPercent = 0;
      gpu.memoryUsedDescription = "Unavailable";
    });
    st.disks.forEach(function (disk) {
      disk.storageUsedPercent = 0;
      disk.storageUsedDescription = "Unavailable";
      disk.topUser = "Unavailable";
      disk.topUserPercent = 0;
      disk.topUserDescription = "Unavailable";
    });
    st.memory.memoryUsedPercent = 0;
    st.memory.memoryUsedDescription = "Unavailable";
    st.load.loadPercent = 0;
    st.load.loadDescription = "Unavailable";
    st.partitions = [];
  }
  // Use number of seconds since last retrieval as measurement of age
  st.age = clientAge;

  // Mark update as recent if both:
  // 1. The last retrieval yielded a status with a new timestamp and
  // 2. The last retrieval was relatively recent (last few seconds)
  st.isRecent =
    st.timestamp !== st.previousTimestamp && st.age < RECENTNESS_THRESHOLD;
}

export default {
  data() {
    return {
      statuses: {},
      lastUpdateDatetime: null,
    };
  },
  computed: {
    sortedStatuses() {
      return sortBy(Object.values(this.statuses), "host");
    },
  },
  methods: {
    retrieveStatuses() {
      const axiosOptions = { headers: { Accept: "application/json" } };
      NODES.forEach((node) =>
        axios
          .get(`/${node}.json`, axiosOptions)
          .then((response) => this.processStatusUpdate(response.data))
          .catch((error) => console.error(error))
      );
    },
    processStatusUpdate(st) {
      this.lastUpdateDatetime = new Date();

      st.previousTimestamp =
        st.host in this.statuses ? this.statuses[st.host].timestamp : null;
      st.datetime = new Date(st.timestamp * 1000);
      st.retrievedDatetime = new Date();
      st.gpus.forEach(function (gpu) {
        gpu.utilizationPercent = Math.ceil(100 * gpu.utilization);
        gpu.memoryUsedPercent = Math.ceil(
          100 * (gpu.memory_used / gpu.memory_total)
        );
        const memoryUsedStr = `${gpu.memory_used.toString()} ${
          gpu.memory_unit
        }`;
        const memoryTotalStr = `${gpu.memory_total.toString()} ${
          gpu.memory_unit
        }`;
        gpu.memoryUsedDescription = `${memoryUsedStr} used / ${memoryTotalStr} total`;
      });
      st.disks.forEach(function (disk) {
        disk.storageUsedPercent = Math.ceil(
          100 * (disk.storage_used / disk.storage_total)
        );
        const storageUsedStr = `${disk.storage_used.toString()} ${
          disk.storage_unit
        }`;
        const storageTotalStr = `${disk.storage_total.toString()} ${
          disk.storage_unit
        }`;
        disk.storageUsedDescription = `${storageUsedStr} used / ${storageTotalStr} total`;
        const topUserEntry = last(sortBy(
          Object.entries(disk.per_user.storage_used).map(([uid, storage_used]) => ({uid, storage_used})),
          ['storage_used']
        ));
        if (topUserEntry) {
          disk.topUser = topUserEntry.uid;
          disk.topUserPercent = Math.ceil(
            100 * (topUserEntry.storage_used / disk.storage_total)
          );
          disk.topUserDescription = `${topUserEntry.storage_used.toString()} ${
            disk.storage_unit
          }`;
        } else {
          disk.topUser = "";
          disk.topUserPercent = 0;
          disk.topUserDescription = "";
        }
      });
      st.memory.memoryUsedPercent = Math.ceil(
        100 * (st.memory.memory_used / st.memory.memory_total)
      );
      const memoryUsedStr = `${st.memory.memory_used.toString()} ${
        st.memory.memory_unit
      }`;
      const memoryTotalStr = `${st.memory.memory_total.toString()} ${
        st.memory.memory_unit
      }`;
      st.memory.memoryUsedDescription = `${memoryUsedStr} used / ${memoryTotalStr} total`;
      st.load.loadPercent = Math.ceil(
        100 * (st.load.load_avg_5_m / st.load.num_cpus)
      );
      const loadStr = `${st.load.load_avg_5_m.toString()} (five-minute average)`;
      const numCPUsStr = `${st.load.num_cpus.toString()} CPU cores`;
      st.load.loadDescription = `${loadStr} / ${numCPUsStr}`;

      setAge(st);

      this.statuses[st.host] = st;
    },
    setAges() {
      Object.values(this.statuses).forEach(setAge);
    },
  },
  mounted() {
    this.retrieveStatuses();
    setInterval(this.retrieveStatuses, 1000 * RETRIEVAL_RATE);
    this.setAges();
    setInterval(this.setAges, 100);
  },
};
</script>

<style src="bootstrap/dist/css/bootstrap.min.css">
</style>

<style src="bootstrap-icons/font/bootstrap-icons.css">
</style>

<style scoped>
meter {
  width: 2em;
}
.pe-2 {
  padding-right: 1em;
}
.ps-2 {
  padding-left: 1em;
}
</style>
