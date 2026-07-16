# Bypass-BumYT

Công cụ bypass license key cho ứng dụng BumYT TTS.
Đây là 1 app kiểu Vietsub hoạt hình điêu khắc cát bên trung link tải: https://drive.google.com/file/d/1hilLFCGVGk2uLMsUeo5K3wCTnJcdLYfU/view 
Nó nặng lắm nén lại thì 6GB giải nén thầm 14.4GB

## Cách hoạt động

BumYT xác thực key bằng cách gọi API `https://script.google.com/macros/s/...` và kiểm tra phản hồi.
Công cụ này chặn các kết nối đó ở tầng mạng và trả về phản hồi giả (`{"success": true}`).

**Sơ đồ luồng:**

```
BumYT.exe → script.google.com → hosts → 127.0.0.1:443 → bypass_network.py (fake server)
                                                          ↓
                                                   trả về {"success": true}
```

SSL được xác thực bằng CA tự ký: `ca_cert.pem` được thêm vào `certifi/cacert.pem` của app,
và `server_cert.pem` do CA này ký được dùng bởi fake server.

## Yêu cầu / Điều kiện

| Yêu cầu | Chi tiết |
|---------|----------|
| Hệ điều hành | Windows 10/11 |
| Quyền | **Admin** (để sửa hosts, bind port 443, sửa certifi) |
| Python | Có trong PATH (kiểm tra: `python --version`) |
| Port 443 | Không bị ứng dụng khác chiếm (IIS, Skype, ...) |
| Antivirus | Tạm tắt hoặc thêm ngoại lệ nếu bị chặn |

## Các file trong thư mục

### File cốt lõi (cần để chạy)

| File | Mô tả |
|------|-------|
| `bypass_network.py` | **Script chính**: setup hosts, add CA cert, start fake server, launch app, cleanup |
| `run_bypass.bat` | **Launcher**: tự xin quyền admin rồi chạy `bypass_network.py` |
| `server_cert.pem` | Server certificate (CN=script.google.com, do CA ký) |
| `server_key.pem` | Private key của server cert |
| `ca_cert.pem` | Certificate Authority (CA) tự ký — được thêm vào `cacert.pem` |
| `ca_key.pem` | Private key của CA |

### File phụ trợ (có thể xóa)

| File | Mô tả |
|------|-------|
| `fake_server.py` | Fake server cũ (không dùng nữa, logic đã gộp vào `bypass_network.py`) |
| `*.bat` | Các batch thử nghiệm khác |
| `*.py` | Các script thử nghiệm / giải mã khác |

## Hướng dẫn sử dụng

### Bước 1: Kiểm tra

Đảm bảo Python có trong PATH:
```cmd
python --version
```

Nếu không có, tải Python tại [python.org](https://python.org) và cài đặt (nhớ tick "Add Python to PATH").

### Bước 2: Chạy bypass

**Cách 1 (khuyên dùng):**
```cmd
Chuột phải run_bypass.bat → Run as administrator
```

**Cách 2 (thủ công):**
```cmd
Mở Terminal / CMD với quyền Admin
cd đường_dẫn_đến_thư_mục
python bypass_network.py
```

### Bước 3: Nhập key

Khi BumYT mở ra, nhập **bất kỳ key nào** (vd: `test`, `abc123`, ...). Fake server sẽ trả về thành công.

### Bước 4: Kết thúc

Đóng cửa sổ Console để script tự động **cleanup**:
- Khôi phục file hosts
- Khôi phục `certifi/cacert.pem`
- Kill fake server
- Xóa portproxy (nếu có)

## Xử lý lỗi thường gặp

### "Access is denied" / "Yêu cầu admin"

Chạy lại với quyền Administrator. Dùng `run_bypass.bat` (tự xin quyền).

### "Port 443 already in use"

Port 443 đang bị ứng dụng khác chiếm. Kiểm tra bằng:
```cmd
netstat -ano | findstr ":443 "
```
Xác định PID và tắt ứng dụng đó (hoặc dùng `taskkill /F /PID <PID>` với admin).

### "Python not found" / "'python' is not recognized"

Cài Python và tick **"Add Python to PATH"**, hoặc dùng đường dẫn đầy đủ:
```cmd
C:\Users\...\AppData\Local\Programs\Python\Python312\python.exe bypass_network.py
```

### "SSL: CERTIFICATE_VERIFY_FAILED"

Script chưa kịp add CA cert vào `cacert.pem` trước khi app chạy. Chạy lại lần nữa.

### Hosts không có tác dụng

Windows DNS cache có thể chưa được flush. Script tự động chạy `ipconfig /flushdns`.
Nếu vẫn không được, chạy thủ công (admin):
```cmd
ipconfig /flushdns
```

## Lưu ý bảo mật

- Công cụ này **chỉ chạy local**, không gửi dữ liệu ra ngoài.
- Fake server tự động cleanup sau khi đóng console.
- CA cert (`ca_cert.pem`) được tạo cục bộ, không chia sẻ.

## License

Dùng cho mục đích học tập / nghiên cứu.
