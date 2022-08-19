<template>
  <div class="container-sm">
    <header>
      <h1 class="h1-display">BRTX GPU Status</h1>
    </header>

    <main>
      <div v-for="status in sortedStatuses" :key="status.host" class="d-flex">
        <div class="lead pe-2">
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
                : `filter: opacity(${status.uptodatenessPercent}%)`
            "
            :title="`Updated ${status.age} seconds ago`"
          ></i>
          {{ status.host }}
        </div>
        <div v-for="(gpu, i) in status.gpus" :key="i" class="p-1">
          <meter
            min="0"
            max="100"
            :value="gpu.memUsedPercent"
            :title="gpu.memUsedDescription"
          >
            {{ gpu.memUsedDescription }}
          </meter>
        </div>
      </div>
    </main>

    <footer></footer>
  </div>
</template>

<script>
import axios from "axios";
import { sortBy } from "lodash";

const AGE_UNAVAILABLE = 120;

function updateAge(st) {
  st.age = Math.ceil((new Date() - st.datetime) / 1000);
  st.unavailable = st.age >= AGE_UNAVAILABLE;
  try {
    st.uptodateness = Math.min(Math.max(1 - st.age / AGE_UNAVAILABLE, 0), 1);
    if (!Number.isFinite(st.uptodateness)) {
      st.uptodateness = 0;
    }
  } catch {
    st.uptodateness = 0;
  }
  st.uptodatenessPercent = Math.floor(100 * st.uptodateness);
  return st;
}

function processStatus(st) {
  st.datetime = new Date(st.timestamp * 1000);
  updateAge(st);
  st.gpus.forEach(function (gpu) {
    gpu.utilizationPercent = st.unavailable
      ? 0
      : Math.ceil(100 * gpu.utilization);
    gpu.memUsedPercent = st.unavailable
      ? 0
      : Math.ceil(100 * (gpu.memory_used / gpu.memory_total));
    const memUsedStr = Math.ceil(gpu.memory_used / 1000).toString() + " GB";
    const memTotalStr = Math.ceil(gpu.memory_total / 1000).toString() + " GB";
    gpu.memUsedDescription = st.unavailable
      ? "Unavailable"
      : `${memUsedStr} used / ${memTotalStr} total`;
  });
  return st;
}

export default {
  data() {
    return {
      statuses: {},
    };
  },
  computed: {
    sortedStatuses() {
      return sortBy(Object.values(this.statuses), "host");
    },
  },
  methods: {
    fetchStatuses() {
      const app = this;
      const axiosOptions = { headers: { Accept: "application/json" } };
      [601, 602, 603, 604, 605, 606].forEach((brtxIndex) =>
        axios
          .get(`/brtx${brtxIndex}.json`, axiosOptions)
          .then(function (response) {
            app.statuses[response.data.host] = processStatus(response.data);
          })
          .catch((error) => console.error(error))
      );
    },
    updateAges() {
      Object.values(this.statuses).forEach(updateAge);
    },
  },
  mounted() {
    this.fetchStatuses();
    setInterval(this.fetchStatuses, 1000 * 60);
    this.updateAges();
    setInterval(this.updateAges, 1000);
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
