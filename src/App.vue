<template>
  <div class="container-sm">
    <header>
      <h1 class="h1-display">
        BRTX GPU Status
      </h1>
    </header>

    <main>
      <div v-for="status in sortedStatuses" :key="status.host" class="d-flex">
        <div class="lead pe-2">
          <i class="bi" :class="{'bi-hourglass-top': status.age < 60, 'text-muted': status.age < 60, 'bi-hourglass-split': status.age >= 60 && status.age < 120, 'text-dark': status.age >= 60 && status.age < 120, 'bi-hourglass-bottom': status.age > 120, 'text-danger': status.age > 120}"></i>
          {{ status.host }}
        </div>
        <div v-for="(gpu, i) in status.gpus" :key="i" class="p-1">
          <meter min="0" max="100" :value="gpu.memUsedPercent" :title="`${gpu.memUsedPercent}%`">
            Load: {{ gpu.memUsedPercent }}%
          </meter>
        </div>
      </div>
    </main>

    <footer>
    </footer>
  </div>
</template>

<script>
import axios from "axios";
import { sortBy } from "lodash";

function processStatus(st) {
  st.datetime = new Date(st.timestamp * 1000);
  st.gpus.forEach(function(gpu) {
    gpu.utilizationPercent = Math.ceil(100 * gpu.utilization);
    gpu.memUsedPercent = Math.ceil(100 * gpu.memory_used / gpu.memory_total);
  });
  return st;
}

export default {
  data() {
    return {
      statuses: {},
    }
  },
  computed: {
    sortedStatuses() {
      return sortBy(Object.values(this.statuses), "host");
    },
  },
  methods: {
    fetchStatuses() {
      const app = this;
      const axiosOptions = {headers: {Accept: "application/json"}};
      [601, 602, 603, 604, 605, 606].forEach((brtxIndex) =>
        axios.get(`/brtx${brtxIndex}.json`, axiosOptions)
          .then(function (response) {
            app.statuses[response.data.host] = processStatus(response.data);
            app.updateAges();
          })
          .catch((error) => console.error(error))
      );
    },
    updateAges() {
      Object.values(this.statuses).forEach((st) =>
        (st.age = (new Date() - st.datetime) / 1000));
    },
  },
  mounted() {
    this.fetchStatuses();
    setInterval(this.fetchStatuses, 1000 * 60);
    this.updateAges();
    setInterval(this.updateAges, 1000);
  },
}
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
