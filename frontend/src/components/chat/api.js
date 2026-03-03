import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY || '';

export async function chatOnce(message) {
  const res = await axios.post(
    `${API_URL}/api/chat`,
    { message },
    {
      headers: {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json',
      },
    },
  );
  return res.data;
}
