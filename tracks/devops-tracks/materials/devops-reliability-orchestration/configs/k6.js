import http from 'k6/http';
import { check } from 'k6';
export const options = {
  scenarios: { fixed_arrival: { executor: 'constant-arrival-rate', rate: 5, timeUnit: '1s', duration: '10s', preAllocatedVUs: 4, maxVUs: 8 } },
  thresholds: { http_req_failed: ['rate<0.02'], http_req_duration: ['p(95)<300'] },
};
export default function () {
  const response = http.get('http://127.0.0.1:8000/work', { timeout: '2s' });
  check(response, { 'work completed': r => r.status === 200 });
}
