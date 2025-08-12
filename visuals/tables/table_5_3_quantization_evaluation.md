**Table 5.3: Qualitative Evaluation of GGUF Quantization Levels**

| Model | Task Assessment | Key Observation |
| --- | --- | --- |
| High-Precision (f16) | Excellent | Gold standard. Provides correct, nuanced, and well-explained outputs. |
| Quantized (Q8_0) | Excellent | No discernible degradation in performance or reasoning ability. |
| Quantized (Q6_K) | Excellent | No discernible degradation in performance or reasoning ability. |
| Quantized (Q5_K_M) | Excellent | No discernible degradation in performance or reasoning ability. |
| Quantized (Q4_K_M) | Excellent | No discernible degradation. The optimal balance of size and performance. |
| Quantized (Q3_K_M) | Good | Functionally correct but with minor losses in explanatory detail. |
| Quantized (Q2_K) | FAIL | Catastrophic failure. Produces hallucinated, non-functional code. |
