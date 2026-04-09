import axios from "axios";
const API_URL = import.meta.env.VITE_API_URL;
const APIKEY = import.meta.env.VITE_APIKEY;

export const SuggestAPI = async (query) => {
    try {
        const response = await axios.get(`${API_URL}/ngram/auto-suggest`, {
            params: {
                q: query,
                top_k: 5
            },
            headers: {
                "Content-Type": "application/json",
                apikey: APIKEY
            }
        });
        console.log(response.data);
        return response.data;
    } catch(err) {
        console.log("<error>", err);
        return { success: false, suggestions: [] };
    }
}