## **Scope and Limitations**  
This section outlines the **scope** and **limitations** of **Infonova**, describing what the system can do and the boundaries of its performance.

---

### 📘 Scope
- Infonova uses datasets from GMA, RAPPLER, Inquirer and Manila Bulletin for training and testing.
- Displays 10 news articles per result page.
- When no suggestion is found, the system falls back to unigram suggestions.
- Mainly supports English words for normalization and processing.


### ⚠️ Limitations
- The model needs to be reloaded to maintain its accuracy.
- Non-English words or mixed-language articles may not be processed correctly.
- It is word based only. It won’t suggest results for partial words (example: typing “compu” won’t suggest “computer”).
- The system is trained on small datasets.
- TF-IDF only counts word frequency, but it cannot recognize synonyms, semantics, or the relationships between words.
- Naive Bayes assumes all words are independent, making it less accurate with context-dependent text. 
