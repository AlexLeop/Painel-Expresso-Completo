import axios from 'axios';
import * as dotenv from 'dotenv';
dotenv.config();

const apiUrl = process.env.EVOLUTION_API_URL;
const apiKey = process.env.EVOLUTION_API_KEY;
const instanceName = process.env.EVOLUTION_INSTANCE_NAME;
const instanceToken = process.env.EVOLUTION_INSTANCE_TOKEN;

export const evolutionApi = axios.create({
  baseURL: apiUrl,
  headers: {
    'apikey': apiKey,
    'Content-Type': 'application/json',
  }
});
