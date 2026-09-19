# Báo Cáo Nhóm - Lab 7: Embedding & Vector Store

**Nhóm:** DDCC  
**Thành viên:** Nguyễn Đức Danh, Bùi Gia Chính, Lê Phan Việt Cường, Nguyễn Quang Duy

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong
> `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết
trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) - Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Georgetown University Library Policies & Services - quy định mượn tài liệu, course reserves, media, thiết
bị, interlibrary loan và quy định sử dụng thư viện.

**Tại sao nhóm chọn chủ đề này?**

Corpus tập trung vào một domain thống nhất nhưng có nhiều loại dịch vụ và nhiều nhóm người dùng (`student`, `faculty`,
`all`). Đặc biệt, chính sách mượn sách và course reserves có thông tin khác nhau theo đối tượng, phù hợp để đánh giá tác
động của metadata filtering và so sánh các chiến lược chunking trên cùng một corpus.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu                             | Nguồn (Source URL)                                                | Ngày lấy / Phiên bản    | Số ký tự sau clean | Metadata đã gán                                                                     |
|---|------------------------------------------|-------------------------------------------------------------------|-------------------------|-------------------:|-------------------------------------------------------------------------------------|
| 1 | Borrowing Books - Faculty                | https://library.georgetown.edu/policies/borrowing/materials/books | 2026-09-19 / not-stated |                287 | `audience=faculty`, `department=library`, `category=borrowing`, `language=en`       |
| 2 | Borrowing Books - Undergraduate Students | https://library.georgetown.edu/policies/borrowing/materials/books | 2026-09-19 / not-stated |                174 | `audience=student`, `department=library`, `category=borrowing`, `language=en`       |
| 3 | Borrowing Media                          | https://library.georgetown.edu/policies/borrowing/materials/media | 2026-09-19 / not-stated |               1192 | `audience=all`, `department=library`, `category=borrowing-media`, `language=en`     |
| 4 | Course Reserves Information for Faculty  | https://library.georgetown.edu/course-reserves/faculty            | 2026-09-19 / not-stated |               3971 | `audience=faculty`, `department=library`, `category=course-reserves`, `language=en` |
| 5 | Course Reserves Information for Students | https://library.georgetown.edu/course-reserves/students           | 2026-09-19 / not-stated |               1818 | `audience=student`, `department=library`, `category=course-reserves`, `language=en` |
| 6 | Equipment Loans                          | https://library.georgetown.edu/equipment                          | 2026-09-19 / not-stated |               2259 | `audience=all`, `department=library`, `category=equipment`, `language=en`           |
| 7 | Interlibrary and Consortium Loans        | https://library.georgetown.edu/loans                              | 2026-09-19 / not-stated |               3211 | `audience=all`, `department=library`, `category=interlibrary-loan`, `language=en`   |
| 8 | Library Use Policies                     | https://library.georgetown.edu/policies/library-use               | 2026-09-19 / not-stated |               2110 | `audience=all`, `department=library`, `category=library-use`, `language=en`         |

**Cách chuẩn hóa corpus**

- Hai tài liệu borrowing được tách theo audience từ cùng trang nguồn: `borrowing-books-undergraduate.md` chỉ giữ quy
  định dành cho undergraduate students; `borrowing-books-faculty.md` chỉ giữ các nhóm faculty.
- Các heading, bảng và danh sách được chuẩn hóa về Markdown để giảm nhiễu retrieval; menu, site title lặp, form artifact
  và navigation text đã được loại bỏ.
- Nội dung nguồn, số liệu, thời hạn và quy định được giữ theo tài liệu crawl; không tự tạo `document_version` khi nguồn
  không công bố.
- Mọi file dùng UTF-8, `doc_id` trùng với filename stem, và `sources.csv` giữ provenance 1-1.

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**

- [x] Corpus có 8 tài liệu, nằm trong yêu cầu 5–10 tài liệu.
- [x] Các URL đã được crawler kiểm `robots.txt`; lượt crawl hoàn tất 8 saved, 0 skipped.
- [x] Corpus chỉ dùng nguồn công khai của Georgetown University Library.
- [x] Mỗi tài liệu có `doc_id`, `title`, `source_url`, `retrieved_at`, `document_version`, `audience`.
- [x] Mỗi tài liệu có thêm `department`, `category`, `language`.
- [x] `sources.csv` khớp 1-1 với 8 file `.md`.
- [x] `audience` có ít nhất hai giá trị khác nhau: `student`, `faculty`, `all`.
- [x] Các tài liệu đã được clean trước khi benchmark.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata    | Kiểu               | Ví dụ giá trị                                                       | Tại sao hữu ích cho retrieval?                                                           |
|--------------------|--------------------|---------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| `doc_id`           | `str`              | `borrowing-books-undergraduate`                                     | ID ổn định của document gốc; dùng để trace chunk và xóa toàn bộ chunks của một document. |
| `title`            | `str`              | `Borrowing Books - Undergraduate Students`                          | Giữ ngữ cảnh và giúp đọc/trace kết quả retrieval.                                        |
| `source_url`       | `str`              | `https://library.georgetown.edu/policies/borrowing/materials/books` | Provenance: truy vết kết quả về trang nguồn.                                             |
| `retrieved_at`     | `str (YYYY-MM-DD)` | `2026-09-19`                                                        | Ghi thời điểm thu thập corpus.                                                           |
| `document_version` | `str`              | `not-stated`                                                        | Theo dõi phiên bản nếu nguồn có nêu; dùng `not-stated` khi nguồn không công bố.          |
| `audience`         | `str`              | `student`, `faculty`, `all`                                         | Field filter bắt buộc của L3A; giúp lọc đúng nhóm người dùng trước similarity search.    |
| `department`       | `str`              | `library`                                                           | Xác định domain/đơn vị sở hữu chính sách.                                                |
| `category`         | `str`              | `borrowing`, `course-reserves`, `equipment`                         | Phân loại dịch vụ/chính sách và có thể dùng làm chiều filter bổ sung.                    |
| `language`         | `str`              | `en`                                                                | Theo dõi ngôn ngữ corpus và lựa chọn embedding phù hợp.                                  |

---

## 2. Thiết kế chiến lược (Strategy Design) - Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Baseline được chạy trên phần body đã loại YAML frontmatter với `chunk_size=700`.

| Tài liệu                        | Chiến lược (Strategy)            | Số lượng Chunk | Độ dài trung bình |
|---------------------------------|----------------------------------|---------------:|------------------:|
| `course-reserves-student`       | FixedSizeChunker (`fixed_size`)  |              3 |             639.7 |
| `course-reserves-student`       | SentenceChunker (`by_sentences`) |              7 |             257.9 |
| `course-reserves-student`       | RecursiveChunker (`recursive`)   |              3 |             605.0 |
| `equipment-loans`               | FixedSizeChunker (`fixed_size`)  |              4 |             602.2 |
| `equipment-loans`               | SentenceChunker (`by_sentences`) |              9 |             248.6 |
| `equipment-loans`               | RecursiveChunker (`recursive`)   |              4 |             563.2 |
| `interlibrary-consortium-loans` | FixedSizeChunker (`fixed_size`)  |              5 |             682.6 |
| `interlibrary-consortium-loans` | SentenceChunker (`by_sentences`) |              9 |             354.8 |
| `interlibrary-consortium-loans` | RecursiveChunker (`recursive`)   |              6 |             533.8 |

**Nhận xét baseline**

- `SentenceChunker` tạo nhiều chunk nhỏ nhất trên cả ba tài liệu, giúp giữ ranh giới câu nhưng làm tăng số lượng vector
  cần lưu và truy xuất.
- `FixedSizeChunker` tạo ít chunk hơn với độ dài trung bình lớn hơn, nhưng có thể cắt ngang ranh giới ngữ nghĩa của
  section/câu.
- `RecursiveChunker` giữ số chunk tương đối thấp trong khi ưu tiên các ranh giới paragraph, dòng và câu trước khi
  fallback sang cắt theo ký tự.

### Chiến lược của từng thành viên

**Nguyễn Đức Danh**

- **Loại chiến lược:** Heading-aware chunking + `RecursiveChunker` fallback.
- **Mô tả & lý do chọn:** Corpus Georgetown Library được chuẩn hóa dưới dạng Markdown với cấu trúc heading rõ ràng như
  `## Book Reserves`, `## Renewals`, `## Fines`, `### Recall Fines`. Chiến lược tách theo heading tận dụng chính cấu
  trúc ngữ nghĩa do tài liệu gốc cung cấp. Nếu một section vượt `chunk_size`, phần body được chia tiếp bằng
  `RecursiveChunker` và heading hierarchy được gắn lại vào từng child chunk để tránh mất ngữ cảnh.
- **Kết quả ingest CP5:** 8 documents → 36 chunks.

**Bùi Gia Chính**

- **Loại chiến lược:** Fixed-size chunking.
- **Mô tả & lý do chọn:** Dùng làm đối chứng đơn giản dựa trên kích thước cố định và overlap. Thành viên cần chạy
  benchmark riêng với cùng harness để có kết quả chính thức.

**Lê Phan Việt Cường**

- **Loại chiến lược:** Recursive chunking.
- **Mô tả & lý do chọn:** Ưu tiên các separator có ý nghĩa như paragraph, dòng và câu trước khi phải cắt theo ký tự.
  Thành viên cần chạy benchmark riêng với cùng harness để có kết quả chính thức.

**Nguyễn Quang Duy**

- **Loại chiến lược:** Sentence-based chunking.
- **Mô tả & lý do chọn:** Giữ ranh giới câu và nhóm nhiều câu thành một chunk. Thành viên cần chạy benchmark riêng với
  cùng harness để có kết quả chính thức.

### So Sánh Giữa Các Thành Viên

| Thành viên         | Chiến lược (Strategy)              | Điểm truy xuất (/10) | Điểm mạnh                                  | Điểm yếu                                                              |
|--------------------|------------------------------------|---------------------:|--------------------------------------------|-----------------------------------------------------------------------|
| Nguyễn Đức Danh    | Heading-aware + Recursive fallback |                <CP6> | Giữ cấu trúc section và heading context    | Có thể cần nhiều chunk khi một câu hỏi cần thông tin từ nhiều section |
| Bùi Gia Chính      | Fixed-size                         |                <CP6> | Đơn giản, ổn định, dễ kiểm soát kích thước | Có thể cắt ngang ranh giới semantic                                   |
| Lê Phan Việt Cường | Recursive                          |                <CP6> | Ưu tiên boundary tự nhiên                  | Không tận dụng trực tiếp heading hierarchy                            |
| Nguyễn Quang Duy   | Sentence-based                     |                <CP6> | Giữ nguyên câu, chunk dễ đọc               | Có thể tạo nhiều chunk nhỏ                                            |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**

> **Điền sau CP6**, dựa trên kết quả benchmark bằng real semantic embeddings và relevance của chunk content, không dựa
> trên mock embeddings.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) - Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng và có thể kiểm chứng từ corpus. Câu Q1 bắt buộc dùng
> `metadata_filter={"audience": "student"}` để phân biệt borrowing policy của sinh viên với faculty.

| # | Câu hỏi (Query)                                                                   | Câu trả lời chuẩn (Gold Answer)                                                                                                                                       | Chunk/section chứa thông tin                                                                  |
|---|-----------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| 1 | How long can I borrow books?                                                      | Đối với undergraduate student: số sách không giới hạn và thời hạn mượn là 6 tuần.                                                                                     | `borrowing-books-undergraduate` - `## Georgetown Users`                                       |
| 2 | How many reserve items may a student borrow at one time?                          | Sinh viên được mượn tối đa 3 reserve items cùng một lúc.                                                                                                              | `course-reserves-student` - `## Book Reserves`                                                |
| 3 | How do I request library equipment, and how far in advance must I reserve it?     | Từ trang thiết bị, chọn “Reserve this item”, đăng nhập tài khoản thư viện và gửi request; reservation phải được thực hiện ít nhất 1 ngày trước.                       | `equipment-loans` - `## Requesting Equipment` và `## Media Equipment Checkout / Reservations` |
| 4 | How long do Interlibrary Loan requests usually take to arrive?                    | Thời gian giao trung bình của Interlibrary Loan là 7–14 ngày làm việc.                                                                                                | `interlibrary-consortium-loans` - `## Items from Other Locations`                             |
| 5 | Where is food allowed in Lauinger Library, and what kinds of food are prohibited? | Food chỉ được phép ở tầng 2 Lauinger Library; ví dụ thực phẩm bị cấm gồm pizza, hamburgers, fries, ice cream, hot subs và các loại đồ ăn có mùi, dầu mỡ hoặc bừa bộn. | `library-use-policy` - `## General Policies`                                                  |

### Tổng hợp chất lượng truy xuất của nhóm

| # | Câu hỏi                                                                           | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú                                               |
|---|-----------------------------------------------------------------------------------|---------------------------------|---------------------------------|-------------------------------------------------------|
| 1 | How long can I borrow books?                                                      | CP6                             | CP6                             | Chạy A/B có và không có `audience=student`            |
| 2 | How many reserve items may a student borrow at one time?                          | CP6                             | CP6                             | Chấm theo nội dung chunk, không chỉ theo `doc_id`     |
| 3 | How do I request library equipment, and how far in advance must I reserve it?     | CP6                             | CP6                             | Gold answer nằm ở hai section khác nhau               |
| 4 | How long do Interlibrary Loan requests usually take to arrive?                    | CP6                             | CP6                             | Cần chunk chứa chính xác thông tin 7–14 business days |
| 5 | Where is food allowed in Lauinger Library, and what kinds of food are prohibited? | CP6                             | CP6                             | Cần chunk chứa cả location và ví dụ food bị cấm       |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**

> **Đánh giá chính thức ở CP6.** Q1 được thiết kế để kiểm tra trực tiếp metadata filtering: corpus có borrowing policy
> cho `student` và `faculty` với thời hạn khác nhau, nên chạy A/B giữa retrieval không filter và
> `metadata_filter={"audience": "student"}` sẽ cho thấy filter có giúp loại tài liệu sai đối tượng hay không.

---

## 4. Thuyết trình (Demo) & Bài học nhóm - Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**

> [Điền sau CP6.]

**Bài học rút ra khi so sánh trong nhóm:**

> [Điền sau CP6.]

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**

> [Điền sau CP6.]

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí                                 | Điểm tự đánh giá |
|------------------------------------------|-----------------:|
| Lựa chọn tài liệu (Document Set Quality) |             / 10 |
| Thiết kế chiến lược (Strategy Design)    |             / 15 |
| Chất lượng truy xuất (Retrieval Quality) |             / 10 |
| Thuyết trình (Demo)                      |              / 5 |
| **Tổng phần nhóm**                       |         **/ 40** |
