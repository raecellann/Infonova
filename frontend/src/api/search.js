import axios from "axios";
const API_URL = import.meta.env.VITE_API_URL;
const APIKEY = import.meta.env.VITE_APIKEY;

export const SearchAPI = async (query, limit = 10, offset = 0) => {
    try {
        const response = await axios.get(
            `${API_URL}/tfidf/search?query=${encodeURIComponent(query)}&limit=${limit}&offset=${offset}`,
            {
                headers: {
                    "Content-Type": "application/json",
                    apikey: APIKEY
                }
            }
        )
        
        const totalCount = response.data.total || response.data.count || 0;
        // console.log('API Response:', response.data);
        
        return {
            results: response.data.results || [],
            total: totalCount,
            has_more: response.data.has_more || false,
            count: response.data.count || 0
        }
    } catch(err) {
        console.error("Search API error:", err)
        throw err
    }
}