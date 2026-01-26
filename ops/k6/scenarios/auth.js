import http from 'k6/http';
import { check, sleep, fail } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { BASE_URL, defaultHeaders, stages, CREDENTIALS, API_ENDPOINTS } from '../config.js';

const loginErrorRate = new Rate('login_errors');
const loginDuration = new Trend('login_duration');
const successfulLogins = new Counter('successful_logins');
const failedLogins = new Counter('failed_logins');

export const options = {
    stages: stages.smoke,
    thresholds: {
        http_req_duration: ['p(95)<500'],
        http_req_failed: ['rate<0.01'],
        login_errors: ['rate<0.01'],
        login_duration: ['p(95)<500', 'p(99)<800'],
    },
};

export function setup() {
    if (!CREDENTIALS.email || !CREDENTIALS.password) {
        console.warn('⚠️  TEST_USER_EMAIL and TEST_USER_PASSWORD not set. Using mock credentials.');
    }
    return {
        email: CREDENTIALS.email || 'test@example.com',
        password: CREDENTIALS.password || 'testpassword123',
    };
}

export default function (data) {
    const payload = JSON.stringify({
        email: data.email,
        password: data.password,
    });

    const loginRes = http.post(`${BASE_URL}${API_ENDPOINTS.login}`, payload, {
        headers: defaultHeaders,
        tags: { name: 'login' },
    });

    loginDuration.add(loginRes.timings.duration);

    const loginSuccess = check(loginRes, {
        'login status is 200': (r) => r.status === 200,
        'login response time < 500ms': (r) => r.timings.duration < 500,
        'login returns token': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.access_token !== undefined || body.token !== undefined;
            } catch {
                return false;
            }
        },
    });

    if (loginSuccess) {
        successfulLogins.add(1);
    } else {
        failedLogins.add(1);
    }

    loginErrorRate.add(!loginSuccess);

    sleep(1);

    testInvalidLogin();
}

function testInvalidLogin() {
    const invalidPayload = JSON.stringify({
        email: 'invalid@example.com',
        password: 'wrongpassword',
    });

    const invalidRes = http.post(`${BASE_URL}${API_ENDPOINTS.login}`, invalidPayload, {
        headers: defaultHeaders,
        tags: { name: 'login_invalid' },
    });

    check(invalidRes, {
        'invalid login returns 401 or 400': (r) => r.status === 401 || r.status === 400 || r.status === 422,
        'invalid login response time < 500ms': (r) => r.timings.duration < 500,
    });

    sleep(0.5);
}

export function handleSummary(data) {
    const { metrics } = data;
    let summary = '\n=== AUTH TEST SUMMARY ===\n\n';

    if (metrics.login_duration) {
        summary += `Login Duration:\n`;
        summary += `  - avg: ${metrics.login_duration.values.avg.toFixed(2)}ms\n`;
        summary += `  - p95: ${metrics.login_duration.values['p(95)'].toFixed(2)}ms\n`;
    }

    if (metrics.successful_logins) {
        summary += `\nSuccessful Logins: ${metrics.successful_logins.values.count}\n`;
    }

    if (metrics.failed_logins) {
        summary += `Failed Logins: ${metrics.failed_logins.values.count}\n`;
    }

    if (metrics.login_errors) {
        summary += `Login Error Rate: ${(metrics.login_errors.values.rate * 100).toFixed(2)}%\n`;
    }

    return { 'stdout': summary };
}
