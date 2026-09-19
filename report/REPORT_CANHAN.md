# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Lê Phan Việt Cường
**Nhóm:** DDCC
**Ngày:** 2026-09-19

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Độ tương tự cosine cao nghĩa là hai embedding có hướng gần nhau trong không gian vector. Với text, điều đó thường cho thấy hai đoạn nói về ý nghĩa hoặc chủ đề gần nhau, dù có thể không dùng đúng cùng từ.

**Ví dụ có độ tương tự CAO:**
- Câu A: Sinh viên cần nộp đơn xin gia hạn thời hạn trả sách trực tuyến.
- Câu B: Người học có thể yêu cầu kéo dài ngày đến hạn mượn tài liệu qua website thư viện.
- Tại sao tương đồng: Hai câu diễn đạt cùng một hành động và mục đích (gia hạn tài liệu thư viện) nhưng dùng nhiều từ vựng khác nhau.

**Ví dụ có độ tương tự THẤP:**
- Câu A: Thư viện mở cửa đến 22 giờ vào các ngày trong tuần.
- Câu B: Máy ảnh cần được sạc đầy pin trước khi quay phim.
- Tại sao khác: Hai câu nói về hai chủ đề và quan hệ ngữ nghĩa gần như không liên quan.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine so sánh góc (hướng) giữa các vector nên tập trung vào mẫu ý nghĩa thay vì độ lớn tuyệt đối. Độ dài văn bản hoặc độ lớn embedding có thể khác nhau nhưng không nhất thiết làm đổi ý nghĩa; do đó cosine thường phù hợp hơn Euclid để so sánh văn bản.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:* `ceil((10000 - 50) / (500 - 50)) = ceil(9950 / 450) = ceil(22.111...)`.
> *Đáp án:* **23 chunks**. Đã kiểm lại bằng `FixedSizeChunker(chunk_size=500, overlap=50)` với chuỗi 10,000 ký tự và nhận đúng 23 chunks.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Khi `overlap=100`, số chunk là `ceil((10000 - 100) / (500 - 100)) = ceil(9900 / 400) = 25`; kiểm tra bằng `FixedSizeChunker` cũng cho 25. Overlap lớn hơn giúp ý hoặc ngữ cảnh nằm ở ranh giới chunk vẫn xuất hiện trong chunk kế tiếp, có thể cải thiện retrieval, đổi lại tốn thêm embedding, lưu trữ và thời gian tìm kiếm.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Tôi tách ở vị trí sau dấu kết thúc câu bằng regex `(?<=[.!?])(?:\s+|$)`, vì lookbehind giữ lại dấu câu trong output. Sau đó tôi nhóm tối đa `max_sentences_per_chunk` câu và bỏ whitespace thừa; text rỗng trả `[]`. Một giới hạn đã biết là regex đơn giản này vẫn có thể tách sai chữ viết tắt như `TS.`, `v.v.` hoặc số thập phân.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán ưu tiên các separator lớn (`\n\n`, `\n`, `. `, space, rồi đến ký tự), chỉ đệ quy xuống separator nhỏ hơn khi một mảnh vượt `chunk_size`. Các mảnh nhỏ liền kề được gom ngược lên đến gần giới hạn để tránh tạo chunk vụn. Base case là text rỗng, mảnh đã không vượt giới hạn, hoặc hết separator thì cắt theo ký tự để luôn tiến triển.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Store dùng danh sách record in-memory; mỗi `Document` đầu vào tạo đúng một record gồm ID lưu trữ, content, metadata đã copy và embedding. `search` embedding query, tính dot product với embedding của mọi record, sắp xếp giảm dần theo score và chỉ trả `top_k`; embedding không được đưa vào kết quả để output dễ đọc. Mock embedder chuẩn hóa vector nên dot product của nó tương đương cosine, nhưng chỉ dùng để kiểm thử cấu trúc chứ không đánh giá ngữ nghĩa.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> `search_with_filter` lọc metadata trước rồi dùng chung hàm tìm kiếm với tập ứng viên đã lọc, tránh việc top-k bị chiếm bởi tài liệu sai audience. Khi tạo record, metadata được copy và giữ `doc_id` gốc nếu tầng chunking đã cung cấp; `delete_document` loại bỏ toàn bộ record có `metadata['doc_id']` trùng ID được yêu cầu và trả về trạng thái thành công.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Agent truy xuất top-k, đánh số từng chunk `[1]`, `[2]` và kèm URL nguồn (hoặc source/doc_id dự phòng) trong phần context. Prompt yêu cầu LLM chỉ dựa vào context, trích dẫn số chunk hỗ trợ và nói không biết khi context không chứa câu trả lời. Nếu store rỗng, agent trả thông báo ngay để không gọi LLM vô ích.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
pytest tests/ -v
============================= test session starts =============================
collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED

============================= 42 passed in 0.10s =============================
```

**Số lượng bài test vượt qua (pass):** **42 / 42**

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Equipment-reservation query | Equipment passage with “Reserve this item” and “at least 1 day in advance” | cao | 0.8050 | Đúng |
| 2 | ILL-arrival query | ILL passage with “7–14 business days” | cao | 0.7431 | Đúng |
| 3 | Food-policy query | Food-policy passage with “second floor” and prohibited food | cao | 0.9275 | Đúng |
| 4 | Book-loan query | Equipment-request passage | thấp | 0.5955 | Đúng |
| 5 | Reserve-item query | Food-policy passage | thấp | 0.5897 | Đúng |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Hai cặp dự đoán thấp vẫn gần 0.59 vì đều cùng domain thư viện đại học và chia sẻ ngữ cảnh như “borrow”, “library”, hoặc “student”. Embedding semantic không chỉ so khớp từ khóa; cần diễn giải score tương đối với các ứng viên cùng corpus. Các điểm trên dùng `gemini-embedding-001` và cache theo hash.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | How long can I borrow books? | `borrowing-books-undergraduate` — unlimited books, 6 weeks | 0.7090 | Có, top-1 chứa đủ marker gold | Context đủ để trả lời: undergraduate students borrow unlimited books for 6 weeks. |
| 2 | How many reserve items may a student borrow at one time? | `course-reserves-student` — up to three items | 0.8345 | Có, top-1 chứa marker gold | Context đủ để trả lời: up to three reserve items. |
| 3 | How do I request library equipment, and how far in advance must I reserve it? | `equipment-loans` — Reserve this item, HoyaSearch, at least 1 day | 0.8050 | Có, top-1 chứa đủ marker gold | Context đủ để trả lời quy trình và hạn đặt trước. |
| 4 | How long do Interlibrary Loan requests usually take to arrive? | `interlibrary-consortium-loans` — 7–14 business days | 0.7431 | Có, top-1 chứa marker gold | Context đủ để trả lời: 7–14 business days. |
| 5 | Where is food allowed in Lauinger Library, and what kinds of food are prohibited? | `library-use-policy` — second floor + prohibited-food list | 0.9275 | Có, top-1 chứa đủ marker gold | Context đủ để trả lời vị trí và các loại food bị cấm. |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** **5 / 5** theo content-level check với `gemini-embedding-001`; mọi Q1–Q5 đều có gold chunk ở top-1 và chứa đủ marker của gold answer.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Không được chấm chỉ theo `doc_id`: benchmark kiểm thêm các content marker trong top-3. Với Gemini embedding, Recursive đạt 10/10 proxy và mỗi gold chunk ở top-1 có marker đáp án. A/B ở Q1 cho thấy filter vẫn loại được tài liệu faculty ở top-3, nhưng top-1 đã đúng cả khi không lọc; vì vậy Q1 hiện chưa phải bằng chứng mạnh rằng filter là bắt buộc.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 10 / 10 |
| **Tổng phần cá nhân** | **60 / 60** |
