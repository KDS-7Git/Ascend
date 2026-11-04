import http from 'k6/http';
import { check } from 'k6';
export const options = {
  scenarios: { small: { executor: 'constant-arrival-rate', rate: 4, timeUnit: '1s', duration: '5s', preAllocatedVUs: 2, maxVUs: 4 } },
  thresholds: { http_req_failed: ['rate<0.05'] },
};
export default function () {
  const r = http.get('http://127.0.0.1:8000/version', { timeout: '2s' });
  check(r, { 'status is 200': (x) => x.status === 200 });
}
