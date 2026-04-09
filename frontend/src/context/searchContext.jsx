// SearchContext.jsx
import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { SearchAPI } from '../api/search';
import { SuggestAPI } from '../api/suggest';
import { useToast } from './ToastContext';

const SearchContext = createContext();

// Constants for localStorage keys
const SEARCH_CACHE_KEY = 'infonova_search_cache';
const CACHE_EXPIRY_KEY = 'infonova_cache_expiry';
const CACHE_DURATION = 1 * 60 * 1000; // 1 minute in milliseconds

// Pagination constants
const DEFAULT_LIMIT = 10;

// Safe localStorage access utility
const safeLocalStorage = {
  getItem: (key) => {
    if (typeof window === 'undefined' || typeof localStorage === 'undefined') {
      return null;
    }
    try {
      return localStorage.getItem(key);
    } catch (error) {
      console.warn('localStorage get error:', error);
      return null;
    }
  },
  
  setItem: (key, value) => {
    if (typeof window === 'undefined' || typeof localStorage === 'undefined') {
      return;
    }
    try {
      localStorage.setItem(key, value);
    } catch (error) {
      console.warn('localStorage set error:', error);
    }
  },
  
  removeItem: (key) => {
    if (typeof window === 'undefined' || typeof localStorage === 'undefined') {
      return;
    }
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.warn('localStorage remove error:', error);
    }
  },
  
  clear: () => {
    if (typeof window === 'undefined' || typeof localStorage === 'undefined') {
      return;
    }
    try {
      localStorage.clear();
    } catch (error) {
      console.warn('localStorage clear error:', error);
    }
  }
};

export function SearchProvider({ children }) {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [hasHydrated, setHasHydrated] = useState(false);
  
  // Pagination state
  const [pagination, setPagination] = useState({
    offset: 0,
    limit: DEFAULT_LIMIT,
    total: 0,
    hasMore: false
  });
  
  // Use state for the timeout
  const [suggestTimeout, setSuggestTimeout] = useState(null);

  // Load cached results only after client-side hydration
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const cachedData = getCachedResults();
      if (cachedData) {
        setResults(cachedData.results || []);
        setQuery(cachedData.query || '');
        setPagination(cachedData.pagination || {
          offset: 0,
          limit: DEFAULT_LIMIT,
          total: cachedData.results?.length || 0,
          hasMore: false
        });
      }
      setHasHydrated(true);
    }
  }, []);

  // Helper function to get cached results
  const getCachedResults = () => {
    // Don't attempt to read from localStorage during SSR
    if (typeof window === 'undefined') {
      return null;
    }
    
    try {
      const cached = safeLocalStorage.getItem(SEARCH_CACHE_KEY);
      const expiry = safeLocalStorage.getItem(CACHE_EXPIRY_KEY);
      
      if (!cached || !expiry) return null;
      
      const now = Date.now();
      if (now > parseInt(expiry)) {
        // Cache expired, clear it
        clearCache();
        return null;
      }
      
      return JSON.parse(cached);
    } catch (error) {
      console.error('Error reading cache:', error);
      clearCache();
      return null;
    }
  };

  // Helper function to cache results
  const cacheResults = (searchQuery, searchResults, searchPagination) => {
    // Don't attempt to write to localStorage during SSR
    if (typeof window === 'undefined') {
      return;
    }
    
    try {
      const cacheData = {
        query: searchQuery,
        results: searchResults,
        pagination: searchPagination,
        timestamp: Date.now()
      };
      
      safeLocalStorage.setItem(SEARCH_CACHE_KEY, JSON.stringify(cacheData));
      safeLocalStorage.setItem(CACHE_EXPIRY_KEY, (Date.now() + CACHE_DURATION).toString());
    } catch (error) {
      console.error('Error caching results:', error);
    }
  };

  // Helper function to clear cache
  const clearCache = () => {
    // Don't attempt to clear localStorage during SSR
    if (typeof window === 'undefined') {
      return;
    }
    
    try {
      safeLocalStorage.removeItem(SEARCH_CACHE_KEY);
      safeLocalStorage.removeItem(CACHE_EXPIRY_KEY);
    } catch (error) {
      console.error('Error clearing cache:', error);
    }
  };

  // Check if we have valid cached results for a query
  const getCachedResultsForQuery = (searchQuery) => {
    // Don't attempt to read from localStorage during SSR
    if (typeof window === 'undefined') {
      return null;
    }
    
    const cachedData = getCachedResults();
    if (cachedData && cachedData.query === searchQuery) {
      return {
        results: cachedData.results,
        pagination: cachedData.pagination
      };
    }
    return null;
  };

  // Fetch suggestions with proper debouncing using useRef
  const fetchSuggestions = useCallback(async (q) => {
    if (!q.trim()) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }
    
    // Clear existing timeout
    if (suggestTimeout) {
      clearTimeout(suggestTimeout);
    }
    
    // Set new timeout
    const newTimeout = setTimeout(async () => {
      try {
        const result = await SuggestAPI(q);
        if (result.success && result.suggestions?.length > 0) {
          setSuggestions(result.suggestions);
          setShowSuggestions(true);
        } else {
          setSuggestions([]);
          setShowSuggestions(false);
        }
      } catch (err) {
        console.error('Error fetching suggestions:', err);
        setSuggestions([]);
        setShowSuggestions(false);
      }
    }, 300);
    setSuggestTimeout(newTimeout);
  }, []);

  // Get the toast function from the context
  const { showToast } = useToast();
  
  // Handle search using SearchAPI
  const search = async (q, isLoadMore = false) => {
    if (!q.trim()) return;
    
    const newOffset = isLoadMore ? pagination.offset + pagination.limit : 0;
    
    console.log('Search called:', { q, isLoadMore, newOffset }); // Debug log
    
    if (isLoadMore) {
      setLoadingMore(true);
    } else {
      setLoading(true);
      setQuery(q);
      setShowSuggestions(false);
    }
    
    // Clear suggestion timeout when searching
    if (suggestTimeout) {
      clearTimeout(suggestTimeout);
    }
    
    try {
      // Check cache first (only on client side) - but not for loadMore
      const cachedData = !isLoadMore && typeof window !== 'undefined' ? getCachedResultsForQuery(q) : null;
      
      if (cachedData && !isLoadMore) {
        console.log('Using cached results for:', q);
        setResults(cachedData.results || []);
        setPagination(cachedData.pagination || {
          offset: 0,
          limit: DEFAULT_LIMIT,
          total: cachedData.results?.length || 0,
          hasMore: false
        });
        
        // Show notification for cached results
        if (cachedData.results.length > 0) {
          showToast(`Found ${cachedData.results.length} result${cachedData.results.length !== 1 ? 's' : ''} for "${q}"`, 'success');
        } else {
          showToast(`No results found for "${q}"`, 'warning');
        }
      } else {
        console.log('Fetching fresh results for:', q, 'limit:', pagination.limit, 'offset:', newOffset);
        const response = await SearchAPI(q, pagination.limit, newOffset);
        const freshResults = response.results || [];
        const totalResults = response.total || 0;
        const hasMoreResults = response.has_more || false;
        
        console.log('API returned:', { 
          resultsCount: freshResults.length, 
          total: totalResults, 
          hasMore: hasMoreResults 
        }); // Debug log
        
        if (isLoadMore) {
          // Append new results for loadMore
          setResults(prev => {
            const updated = [...prev, ...freshResults];
            console.log('Updated results count:', updated.length); // Debug log
            return updated;
          });
        } else {
          // Replace results for new search
          setResults(freshResults);
        }
        
        // Update pagination
        const newPagination = {
          offset: newOffset,
          limit: pagination.limit,
          total: totalResults,
          hasMore: hasMoreResults
        };
        
        console.log('New pagination:', newPagination); // Debug log
        setPagination(newPagination);
        
        // Show notification
        if (!isLoadMore) {
          if (freshResults.length > 0) {
            showToast(`Found ${totalResults} result${totalResults !== 1 ? 's' : ''} for "${q}"`, 'success');
          } else {
            showToast(`No results found for "${q}"`, 'warning');
          }
        } else if (freshResults.length > 0) {
          showToast(`Loaded ${freshResults.length} more articles`, 'info');
        }
        
        // Cache the new results (only on client side and not for loadMore)
        if (typeof window !== 'undefined' && !isLoadMore) {
          cacheResults(q, freshResults, newPagination);
        }
      }
    } catch (err) {
      console.error('Search error:', err);
      if (!isLoadMore) {
        setResults([]);
      }
      showToast('An error occurred while searching', 'error');
      // Clear cache on error to ensure fresh data next time (only on client side)
      if (typeof window !== 'undefined' && !isLoadMore) {
        clearCache();
      }
    } finally {
      if (isLoadMore) {
        setLoadingMore(false);
      } else {
        setLoading(false);
      }
    }
  };

  // Load more results
  const loadMore = useCallback(() => {
    console.log('loadMore called:', { hasMore: pagination.hasMore, loadingMore }); // Debug log
    if (pagination.hasMore && !loadingMore && query) {
      search(query, true); // Pass true to indicate this is a loadMore request
    }
  }, [query, pagination.hasMore, loadingMore, search]);

  // Clear search results and cache
  const clearSearch = () => {
    setQuery('');
    setResults([]);
    setSuggestions([]);
    setShowSuggestions(false);
    setPagination({
      offset: 0,
      limit: DEFAULT_LIMIT,
      total: 0,
      hasMore: false
    });
    if (typeof window !== 'undefined') {
      clearCache();
    }
  };

  // Force refresh (ignore cache)
  const refreshSearch = async () => {
    if (!query.trim()) return;
    
    setLoading(true);
    try {
      console.log('Force refreshing results for:', query);
      const response = await SearchAPI(query, pagination.limit, 0);
      const freshResults = response.results || [];
      const totalResults = response.total || freshResults.length;
      
      setResults(freshResults);
      
      const newPagination = {
        offset: 0,
        limit: pagination.limit,
        total: totalResults,
        hasMore: freshResults.length < totalResults
      };
      setPagination(newPagination);
      
      // Update cache with fresh results (only on client side)
      if (typeof window !== 'undefined') {
        cacheResults(query, freshResults, newPagination);
      }
    } catch (err) {
      console.error('Refresh search error:', err);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  // Handle input change with debounced suggestions
  const handleInputChange = (value) => {
    setQuery(value);
    if (value.trim()) {
      fetchSuggestions(value);
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
    }
  };

  // Handle suggestion selection
  const selectSuggestion = (suggestion) => {
    const base = query.endsWith(" ") ? query : query + " ";
    const fullQuery = `${base}${suggestion}`;
    setQuery(fullQuery);
    setShowSuggestions(false);
    search(fullQuery);
  };

  // Get cache info (for debugging or display) - client-side only
  const getCacheInfo = () => {
    if (typeof window === 'undefined') {
      return null;
    }
    
    const cachedData = getCachedResults();
    if (!cachedData) return null;
    
    const expiry = safeLocalStorage.getItem(CACHE_EXPIRY_KEY);
    const timeLeft = expiry ? parseInt(expiry) - Date.now() : 0;
    
    return {
      query: cachedData.query,
      resultCount: cachedData.results?.length || 0,
      timestamp: cachedData.timestamp,
      expiresIn: Math.max(0, Math.floor(timeLeft / 1000)), // seconds
      isExpired: timeLeft <= 0,
      formattedExpiration: timeLeft <= 0 ? 'Expired' : 
        `Expires in ${Math.floor(timeLeft / (1000 * 60))}m ${Math.floor((timeLeft % (1000 * 60)) / 1000)}s`
    };
  };

  // Check if we have cached results (client-side only)
  const hasCachedResults = typeof window !== 'undefined' ? !!getCachedResults() : false;

  // Cleanup timeout on unmount and when suggestTimeout changes
  useEffect(() => {
    return () => {
      if (suggestTimeout) {
        clearTimeout(suggestTimeout);
      }
    };
  }, [suggestTimeout]);

  return (
    <SearchContext.Provider value={{
      query,
      results,
      loading,
      loadingMore,
      hasMore: pagination.hasMore,
      pagination,
      suggestions,
      showSuggestions,
      search,
      loadMore,
      setQuery: handleInputChange,
      selectSuggestion,
      setShowSuggestions,
      clearSearch,
      refreshSearch,
      getCacheInfo,
      hasCachedResults,
      hasHydrated // Useful for components to know when client-side hydration is complete
    }}>
      {children}
    </SearchContext.Provider>
  );
}

export function useSearch() {
  const context = useContext(SearchContext);
  if (!context) {
    throw new Error("useSearch() must be used within a <SearchProvider>");
  }
  return context;
}