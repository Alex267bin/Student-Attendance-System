# Báo cáo tổng hợp lỗi phát triển

## 1. Thông tin chung
**Nhánh kiểm tra:** `feature/nhanhc-qa-testing`  

Tài liệu này tổng hợp các lỗi phát hiện trong quá trình chạy, kiểm thử và triển khai hệ thống điểm danh sinh viên. Các lỗi được chia thành lỗi trong mã nguồn và lỗi môi trường/cách vận hành.

## 2. Lỗi trong mã nguồn

### 2.1. Frontend gọi sai địa chỉ backend

Biểu hiện: Người dùng không thể đăng nhập khi mở frontend qua URL public của GitHub Codespaces.
Nguyên nhân: API client gọi cố định `http://localhost:8000`. Khi truy cập từ trình duyệt bên ngoài container, `localhost` trỏ về máy người dùng thay vì backend trong Codespace.
Ảnh hưởng: Các chức năng đăng nhập, đăng ký và gọi API không hoạt động trên môi trường public.
Xử lý: Đổi API base URL mặc định thành URL tương đối. Frontend sử dụng proxy `/api` của Vite hoặc Nginx để chuyển request đến backend.
Trạng thái: Đã khắc phục

### 2.2. Chưa có chức năng đăng ký tài khoản

Biểu hiện:Test case TC03 không thể thực hiện.
Nguyên nhân: Backend chưa có endpoint `/api/auth/register`, frontend chưa có trang đăng ký và client chưa có phương thức gọi API đăng ký.
Ảnh hưởng: Người dùng không thể tự tạo tài khoản Student từ giao diện.
Xử lý:
  - Thêm endpoint `POST /api/auth/register`.
  - Thêm phương thức `register()` trong API client.
  - Thêm route `/register`.
  - Thêm trang tạo tài khoản Student.
  - Thêm liên kết từ trang Login đến trang Register.
- Trạng thái: Đã khắc phục.

### 2.3. Backend có lỗi cú pháp ở dòng import

- **Biểu hiện:** Bộ test backend không thể khởi động và báo lỗi `SyntaxError`.
- **Nguyên nhân:** Các dòng import bị nối sai thành `import sqlite3import json`.
- **Ảnh hưởng:** Toàn bộ API backend không thể chạy.
- **Xử lý:** Chuẩn hóa lại các dòng import trong `backend/api.py`.
- **Trạng thái:** Đã khắc phục.

### 2.4. Tài khoản kiểm thử không tồn tại trong database thật

- **Biểu hiện:** Tài khoản sử dụng trong test đăng nhập được trong test fixture nhưng không đăng nhập được trên giao diện thật.
- **Nguyên nhân:** Test sử dụng database tạm thời; các tài khoản không được tạo trong file `attendance.db` đang chạy.
- **Ảnh hưởng:** Không thể kiểm thử đăng nhập trực tiếp trên frontend.
- **Xử lý:** Tạo các tài khoản mẫu trong database thật:
  - `admin / admin-pass`
  - `lecturer / lecturer-pass`
  - `student / student-pass`
  - `student01 / 123456`
- **Trạng thái:** Đã xử lý cho môi trường kiểm thử.

### 2.5. Nhập sai mã buổi học khi điểm danh

- **Biểu hiện:** Giao diện hiển thị `Session not found`.
- **Nguyên nhân:** Người dùng nhập `USER`, username hoặc mã sinh viên thay vì `session_code` do Lecturer tạo.
- **Ảnh hưởng:** Student không thể gửi điểm danh.
- **Xử lý:** Quy trình đúng là Lecturer tạo session trước, sau đó Student nhập đúng `session_code` được sinh ra.
- **Trạng thái:** Không phải lỗi logic; cần hướng dẫn sử dụng rõ hơn.

### 2.6. Trùng username hoặc email khi chạy lại TC03

- **Biểu hiện:** Giao diện hiển thị lỗi như `Địa chỉ email phải là duy nhất`.
- **Nguyên nhân:** Email và username được thiết kế là duy nhất trong database. Dữ liệu từ lần chạy trước vẫn còn.
- **Ảnh hưởng:** Không thể đăng ký lại cùng một tài khoản test.
- **Xử lý:** Dùng username/email mới hoặc xóa dữ liệu test cũ trước khi chạy lại.
- **Trạng thái:** Đúng theo thiết kế database, không phải lỗi hệ thống.

## 3. Lỗi môi trường và cách vận hành

### 3.1. Chạy lệnh build sai thư mục

- **Biểu hiện:** `npm` báo không tìm thấy `package.json`.
- **Nguyên nhân:** Chạy `npm run build` tại thư mục repository gốc trong khi `package.json` nằm trong `frontend`.
- **Cách xử lý:**

```bash
cd frontend
npm run build
```

- **Trạng thái:** Đã xác định nguyên nhân.

### 3.2. Frontend chưa cài dependencies

- **Biểu hiện:** Lỗi `tsc: not found`.
- **Nguyên nhân:** Thư mục `frontend/node_modules` chưa tồn tại.
- **Cách xử lý:**

```bash
cd frontend
npm install
npm run build
```

- **Trạng thái:** Đã xử lý.

### 3.3. Chạy Python từ sai thư mục

- **Biểu hiện:** Lỗi `ModuleNotFoundError: No module named 'backend'`.
- **Nguyên nhân:** Chạy lệnh Python trong thư mục `frontend`.
- **Cách xử lý:** Chạy từ thư mục gốc dự án:

```bash
cd /workspaces/Student-Attendance-System
python3 -m backend.api
```

- **Trạng thái:** Đã xác định nguyên nhân.

### 3.4. Cổng Codespaces ở chế độ Private

- **Biểu hiện:** URL public của cổng `8000` chuyển hướng đến trang đăng nhập GitHub hoặc trả về `401`.
- **Nguyên nhân:** Port Visibility của Codespaces đang đặt là `Private`.
- **Cách xử lý:** Mở tab **Ports**, chọn cổng cần dùng, sau đó đặt **Port Visibility** thành `Public`.
- **Lưu ý:** Frontend nên được mở qua cổng `5173`; cổng `8000` chỉ phục vụ API.
- **Trạng thái:** Đã xác định nguyên nhân.

### 3.5. Push code bị từ chối do remote có commit mới

- **Biểu hiện:** Git báo `rejected (fetch first)`.
- **Nguyên nhân:** Nhánh trên GitHub có commit mới hơn phiên bản local.
- **Cách xử lý:** Fetch remote, rebase các commit local lên remote, giải quyết conflict rồi push lại.
- **Trạng thái:** Đã xử lý.

## 4. Kết quả kiểm thử sau khắc phục

- Backend test: **18/18 test đạt**.
- Frontend build TypeScript/Vite: **thành công**.
- TC01 đăng nhập đúng: **Đạt**.
- TC02 đăng nhập sai mật khẩu: **Đạt**, trả về HTTP `401`.
- TC03 đăng ký tài khoản: **Đạt**, trả về HTTP `201`.
- Đăng nhập bằng tài khoản vừa đăng ký: **Đạt**, trả về HTTP `200`.
- Code đã được đồng bộ lên nhánh GitHub `feature/nhanhc-qa-testing`.

## 5. Kết luận

Các lỗi chính ảnh hưởng trực tiếp đến chức năng đã được xử lý. Những thông báo về trùng username/email hoặc `Session not found` là kết quả của dữ liệu kiểm thử hoặc thao tác nhập chưa đúng, không phải lỗi nghiêm trọng trong logic hiện tại.

Hệ thống hiện có thể chạy frontend, backend, đăng nhập, đăng ký Student và thực hiện các luồng kiểm thử cơ bản theo yêu cầu.
