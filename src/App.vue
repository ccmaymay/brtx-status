<template>
  <div class="container-sm">
    <header>
      <h1 class="h1-display">BRTX GPU Status</h1>
    </header>

    <main>
      <div
        v-for="status in sortedStatuses"
        :key="status.host"
        class="d-flex align-items-center"
      >
        <div class="mx-1">
          <i
            class="bi"
            :class="{
              'bi-circle-fill': !status.unavailable,
              'bi-question-circle-fill': status.unavailable,
              'text-dark': !status.unavailable,
              'text-warning': status.unavailable,
            }"
            :style="
              status.unavailable
                ? ''
                : `filter: opacity(${status.recentnessPercent}%)`
            "
            :title="`Updated ${Math.floor(status.age)} seconds ago`"
          ></i>
        </div>
        <div class="lead mx-2">
          {{ status.host }}
        </div>
        <div v-for="(gpu, i) in status.gpus" :key="i" class="mx-1">
          <meter
            min="0"
            max="100"
            :value="gpu.memUsedPercent"
            :title="`GPU ${i} memory: ${gpu.memUsedDescription}`"
          >
            GPU {{ i }} memory: {{ gpu.memUsedDescription }}
          </meter>
        </div>
      </div>
    </main>

    <footer class="p-2 mt-4">
      <p class="text-muted">
        <small
          >Last update:
          {{ lastUpdateDatetime ? lastUpdateDatetime : "None" }}</small
        >
      </p>
    </footer>
  </div>
</template>

<script>
import axios from "axios";
import { sortBy } from "lodash";

// Mark node as unavailable at 5 * 60 seconds
const AGE_UNAVAILABLE = 5 * 60;

// Mark update as recent when within last 2 seconds
const RECENTNESS_THRESHOLD = 2;

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

  // Use number of seconds since last retrieval as measurement of age
  st.age = clientAge;

  // Mark update as recent if both:
  // 1. The last retrieval yielded a status with a new timestamp and
  // 2. The last retrieval was relatively recent (last few seconds)
  st.recentness =
    st.timestamp !== st.previousTimestamp
      ? Math.min(Math.max(1 - st.age / RECENTNESS_THRESHOLD, 0), 1)
      : 0;
  st.recentnessPercent = Math.floor(100 * st.recentness);
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
      setAge(st);
      st.gpus.forEach(function (gpu) {
        gpu.utilizationPercent = st.unavailable
          ? 0
          : Math.ceil(100 * gpu.utilization);
        gpu.memUsedPercent = st.unavailable
          ? 0
          : Math.ceil(100 * (gpu.memory_used / gpu.memory_total));
        const memUsedStr = Math.ceil(gpu.memory_used / 1000).toString() + " GB";
        const memTotalStr =
          Math.ceil(gpu.memory_total / 1000).toString() + " GB";
        gpu.memUsedDescription = st.unavailable
          ? "Unavailable"
          : `${memUsedStr} used / ${memTotalStr} total`;
      });
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
</style>
