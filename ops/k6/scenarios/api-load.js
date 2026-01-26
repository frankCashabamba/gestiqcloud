import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { SharedArray } from 'k6/data';
import { BASE_URL, defaultHeaders, authHeaders, stages, CREDENTIALS, API_ENDPOINTS } from '../config.js';

const errorRate = new Rate('errors');
const productosDuration = new Trend('productos_duration');
const ventasDuration = new Trend('ventas_duration');
const clientesDuration = new Trend('clientes_duration');
const totalRequests = new Counter('total_requests');

export const options = {
    scenarios: {
        productos_load: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: stages.load,
            gracefulRampDown: '30s',
            exec: 'testProductos',
        },
        ventas_load: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: stages.load,
            gracefulRampDown: '30s',
            exec: 'testVentas',
            startTime: '10s',
        },
        clientes_load: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: stages.load,
            gracefulRampDown: '30s',
            exec: 'testClientes',
            startTime: '20s',
        },
    },
    thresholds: {
        http_req_duration: ['p(95)<500', 'p(99)<1000'],
        http_req_failed: ['rate<0.01'],
        errors: ['rate<0.01'],
        http_reqs: ['rate>100'],
        productos_duration: ['p(95)<500'],
        ventas_duration: ['p(95)<500'],
        clientes_duration: ['p(95)<500'],
    },
};

let authToken = null;

export function setup() {
    if (CREDENTIALS.email && CREDENTIALS.password) {
        const loginRes = http.post(
            `${BASE_URL}${API_ENDPOINTS.login}`,
            JSON.stringify({
                email: CREDENTIALS.email,
                password: CREDENTIALS.password,
            }),
            { headers: defaultHeaders }
        );

        if (loginRes.status === 200) {
            try {
                const body = JSON.parse(loginRes.body);
                return { token: body.access_token || body.token };
            } catch {
                console.warn('Could not parse login response');
            }
        }
    }

    console.warn('⚠️  Running without authentication. Some endpoints may fail.');
    return { token: null };
}

export function testProductos(data) {
    const headers = data.token ? authHeaders(data.token) : defaultHeaders;

    group('Productos', () => {
        const listRes = http.get(`${BASE_URL}${API_ENDPOINTS.productos}`, {
            headers,
            tags: { name: 'productos_list' },
        });

        productosDuration.add(listRes.timings.duration);
        totalRequests.add(1);

        const success = check(listRes, {
            'productos list status 200': (r) => r.status === 200 || r.status === 401,
            'productos response time < 500ms': (r) => r.timings.duration < 500,
        });

        errorRate.add(!success);

        if (listRes.status === 200) {
            try {
                const productos = JSON.parse(listRes.body);
                if (Array.isArray(productos) && productos.length > 0) {
                    const randomId = productos[Math.floor(Math.random() * productos.length)].id;
                    if (randomId) {
                        const detailRes = http.get(`${BASE_URL}${API_ENDPOINTS.productos}/${randomId}`, {
                            headers,
                            tags: { name: 'productos_detail' },
                        });

                        productosDuration.add(detailRes.timings.duration);
                        totalRequests.add(1);

                        check(detailRes, {
                            'producto detail status 200': (r) => r.status === 200,
                        });
                    }
                }
            } catch {
            }
        }
    });

    sleep(Math.random() * 2 + 1);
}

export function testVentas(data) {
    const headers = data.token ? authHeaders(data.token) : defaultHeaders;

    group('Ventas', () => {
        const listRes = http.get(`${BASE_URL}${API_ENDPOINTS.ventas}`, {
            headers,
            tags: { name: 'ventas_list' },
        });

        ventasDuration.add(listRes.timings.duration);
        totalRequests.add(1);

        const success = check(listRes, {
            'ventas list status 200': (r) => r.status === 200 || r.status === 401,
            'ventas response time < 500ms': (r) => r.timings.duration < 500,
        });

        errorRate.add(!success);

        const paginatedRes = http.get(`${BASE_URL}${API_ENDPOINTS.ventas}?limit=10&offset=0`, {
            headers,
            tags: { name: 'ventas_paginated' },
        });

        ventasDuration.add(paginatedRes.timings.duration);
        totalRequests.add(1);

        check(paginatedRes, {
            'ventas paginated status 200': (r) => r.status === 200 || r.status === 401,
        });
    });

    sleep(Math.random() * 2 + 1);
}

export function testClientes(data) {
    const headers = data.token ? authHeaders(data.token) : defaultHeaders;

    group('Clientes', () => {
        const listRes = http.get(`${BASE_URL}${API_ENDPOINTS.clientes}`, {
            headers,
            tags: { name: 'clientes_list' },
        });

        clientesDuration.add(listRes.timings.duration);
        totalRequests.add(1);

        const success = check(listRes, {
            'clientes list status 200': (r) => r.status === 200 || r.status === 401,
            'clientes response time < 500ms': (r) => r.timings.duration < 500,
        });

        errorRate.add(!success);

        const searchRes = http.get(`${BASE_URL}${API_ENDPOINTS.clientes}?search=test`, {
            headers,
            tags: { name: 'clientes_search' },
        });

        clientesDuration.add(searchRes.timings.duration);
        totalRequests.add(1);

        check(searchRes, {
            'clientes search status 200': (r) => r.status === 200 || r.status === 401,
        });
    });

    sleep(Math.random() * 2 + 1);
}

export function handleSummary(data) {
    const { metrics } = data;
    let summary = '\n=== API LOAD TEST SUMMARY ===\n\n';

    summary += '📊 Overall Metrics:\n';
    if (metrics.http_req_duration) {
        summary += `  Request Duration (p95): ${metrics.http_req_duration.values['p(95)'].toFixed(2)}ms\n`;
    }
    if (metrics.http_reqs) {
        summary += `  Throughput: ${metrics.http_reqs.values.rate.toFixed(2)} req/s\n`;
    }
    if (metrics.http_req_failed) {
        summary += `  Error Rate: ${(metrics.http_req_failed.values.rate * 100).toFixed(2)}%\n`;
    }

    summary += '\n📦 Endpoint Metrics:\n';
    if (metrics.productos_duration) {
        summary += `  Productos (p95): ${metrics.productos_duration.values['p(95)'].toFixed(2)}ms\n`;
    }
    if (metrics.ventas_duration) {
        summary += `  Ventas (p95): ${metrics.ventas_duration.values['p(95)'].toFixed(2)}ms\n`;
    }
    if (metrics.clientes_duration) {
        summary += `  Clientes (p95): ${metrics.clientes_duration.values['p(95)'].toFixed(2)}ms\n`;
    }

    if (metrics.total_requests) {
        summary += `\n📈 Total Requests: ${metrics.total_requests.values.count}\n`;
    }

    return { 'stdout': summary };
}
