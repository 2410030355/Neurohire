const API_BASE_URL = 'http://127.0.0.1:8000';

async function jsonFetch(path, options = {}) {
  const url = `${API_BASE_URL}${path}`;

  let res;
  try {
    res = await fetch(url, {
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
      ...options,
    });
  } catch (fetchError) {
    // Network error or CORS issue
    const message = `Network error: Unable to reach ${API_BASE_URL}. Make sure the backend server is running on port 8000.`;
    const error = new Error(message);
    Object.assign(error, { status: 0, data: null });
    throw error;
  }

  // Handle empty 204 / no-content responses
  const text = await res.text();
  let data = null;
  
  try {
    if (text) {
      data = JSON.parse(text);
    }
  } catch {
    // If it's not JSON, use the raw text
    data = text;
  }

  if (!res.ok) {
    // Extract error message from response
    let message = `Request failed with status ${res.status}`;
    
    if (data && typeof data === 'object' && data.error) {
      message = data.error;
    } else if (typeof data === 'string' && data) {
      message = data;
    }
    
    const error = new Error(message);
    Object.assign(error, { status: res.status, data });
    throw error;
  }

  return data || null;
}

export { API_BASE_URL, jsonFetch };

