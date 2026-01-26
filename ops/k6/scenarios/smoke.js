import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import { BASE_URL, defaultHeaders, stages, API_ENDPOINTS } from '../config.js';

const errorRate = new Rate('errors');
const healthDuration = new Trend('health_duration');
const statusDuration = new Trend('status_duration');

export const options = {
    stages: stages.smoke,
    thresholds: {
        http_req_duration: ['p(95)<500'],
        http_req_failed: ['rate<0.01'],
        errors: ['rate<0.01'],
        health_duration: ['p(95)<200'],
        status_duration: ['p(95)<300'],
    },
};

export default function () {
    const healthRes = http.get(`${BASE_URL}${API_ENDPOINTS.health}`, {
        headers: defaultHeaders,
        tags: { name: 'health' },
    });

    healthDuration.add(healthRes.timings.duration);

    const healthCheck = check(healthRes, {
        'health status is 200': (r) => r.status === 200,
        'health response time < 200ms': (r) => r.timings.duration < 200,
    });

    errorRate.add(!healthCheck);

    sleep(0.5);

    const statusRes = http.get(`${BASE_URL}${API_ENDPOINTS.status}`, {
        headers: defaultHeaders,
        tags: { name: 'status' },
    });

    statusDuration.add(statusRes.timings.duration);

    const statusCheck = check(statusRes, {
        'status endpoint is 200': (r) => r.status === 200,
        'status response time < 300ms': (r) => r.timings.duration < 300,
        'status has valid JSON': (r) => {
            try {
                JSON.parse(r.body);
                return true;
            } catch {
                return false;
            }
        },
    });

    errorRate.add(!statusCheck);

    sleep(1);
}

export function handleSummary(data) {
    return {
        'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    };
}

function textSummary(data, opts) {
    const { metrics } = data;
    let summary = '\n=== SMOKE TEST SUMMARY ===\n\n';

    if (metrics.http_req_duration) {
        summary += `HTTP Request Duration:\n`;
        summary += `  - avg: ${metrics.http_req_duration.values.avg.toFixed(2)}ms\n`;
        summary += `  - p95: ${metrics.http_req_duration.values['p(95)'].toFixed(2)}ms\n`;
    }

    if (metrics.http_req_failed) {
        summary += `\nError Rate: ${(metrics.http_req_failed.values.rate * 100).toFixed(2)}%\n`;
    }

    if (metrics.http_reqs) {
        summary += `Throughput: ${metrics.http_reqs.values.rate.toFixed(2)} req/s\n`;
    }

    return summary;
}
