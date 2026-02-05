/**
 * Configuración base para tests k6 de GestiqCloud
 */

export const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export const CREDENTIALS = {
    email: __ENV.TEST_USER_EMAIL || '',
    password: __ENV.TEST_USER_PASSWORD || '',
};

export const defaultHeaders = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
};

export function authHeaders(token) {
    return {
        ...defaultHeaders,
        'Authorization': `Bearer ${token}`,
    };
}

export const thresholds = {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
    http_reqs: ['rate>100'],
};

export const thresholdsCritical = {
    http_req_duration: ['p(95)<300', 'p(99)<500'],
    http_req_failed: ['rate<0.005'],
    http_reqs: ['rate>200'],
};

export const stages = {
    smoke: [
        { duration: '30s', target: 5 },
        { duration: '1m', target: 5 },
        { duration: '30s', target: 0 },
    ],
    load: [
        { duration: '2m', target: 20 },
        { duration: '5m', target: 20 },
        { duration: '2m', target: 50 },
        { duration: '5m', target: 50 },
        { duration: '2m', target: 0 },
    ],
    stress: [
        { duration: '2m', target: 50 },
        { duration: '5m', target: 100 },
        { duration: '2m', target: 150 },
        { duration: '5m', target: 150 },
        { duration: '5m', target: 0 },
    ],
    spike: [
        { duration: '1m', target: 10 },
        { duration: '30s', target: 200 },
        { duration: '1m', target: 200 },
        { duration: '30s', target: 10 },
        { duration: '2m', target: 0 },
    ],
};

export const API_ENDPOINTS = {
    health: '/health',
    status: '/api/v1/status',
    login: '/api/v1/auth/login',
    productos: '/api/v1/products',
    ventas: '/api/v1/ventas',
    clientes: '/api/v1/clientes',
};
