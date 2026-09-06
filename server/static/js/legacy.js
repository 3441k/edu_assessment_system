/** Small helpers for older browsers (e.g. Firefox < 72 without ?? and ?.). */
function coalesce(value, fallback) {
    return value !== null && value !== undefined ? value : fallback;
}

function hasJsonResponse(res) {
    var ct = res.headers.get('content-type');
    return ct && ct.indexOf('json') !== -1;
}

function apiError(json, status) {
    return (json && json.error) || ('Request failed (' + status + ')');
}

function optionalEl(selector) {
    return document.querySelector(selector);
}
