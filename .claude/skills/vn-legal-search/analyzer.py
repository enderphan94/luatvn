"""Mở rộng keyword + xác định lĩnh vực + cross-law mapping.

Phase 2 — minimal viable. Phase 3 sẽ mở rộng SYNONYM_MAPPING và CROSS_LAW_MAPPING.
"""
from __future__ import annotations

import re

from filter import normalize_vi

# Key (normalized, không dấu) → list các keyword đồng nghĩa / liên quan
# Dùng để mở rộng query khi search song song.
SYNONYM_MAPPING: dict[str, list[str]] = {
    # === THUẾ ===
    "thue thu nhap ca nhan": [
        "thuế thu nhập cá nhân", "TNCN", "thuế TNCN",
        "thu nhập chịu thuế", "thu nhập từ tiền lương tiền công",
    ],
    "thue thu nhap doanh nghiep": [
        "thuế thu nhập doanh nghiệp", "TNDN", "thuế TNDN", "thu nhập chịu thuế doanh nghiệp",
    ],
    "thue gia tri gia tang": [
        "thuế giá trị gia tăng", "GTGT", "thuế GTGT", "VAT",
        "hoàn thuế GTGT", "khấu trừ thuế GTGT",
    ],
    "thue tieu thu dac biet": ["thuế tiêu thụ đặc biệt", "TTĐB", "thuế TTĐB"],
    "thue xuat nhap khau": ["thuế xuất khẩu", "thuế nhập khẩu", "thuế XNK"],
    "thue nha thau": ["thuế nhà thầu", "FCT", "thuế nhà thầu nước ngoài"],
    "tron thue": ["trốn thuế", "khai man thuế", "gian lận thuế", "tội trốn thuế"],
    "hoan thue": ["hoàn thuế", "thủ tục hoàn thuế", "hoàn thuế GTGT"],
    "quyet toan thue": ["quyết toán thuế", "quyết toán TNCN", "tự quyết toán"],

    # === LAO ĐỘNG ===
    "hop dong lao dong": [
        "hợp đồng lao động", "HĐLĐ", "thỏa thuận lao động",
        "hợp đồng việc làm",
    ],
    "sa thai": [
        "sa thải", "chấm dứt hợp đồng lao động",
        "đơn phương chấm dứt HĐLĐ", "kỷ luật lao động",
    ],
    "tien luong": ["tiền lương", "lương tối thiểu", "thang lương", "bậc lương"],
    "lam them gio": [
        "làm thêm giờ", "tăng ca", "OT", "phụ cấp làm thêm giờ",
        "trả lương làm thêm giờ",
    ],
    "nghi phep": ["nghỉ phép", "nghỉ phép năm", "nghỉ hằng năm", "nghỉ lễ tết"],
    "nghi om": ["nghỉ ốm", "nghỉ ốm hưởng BHXH", "ốm đau"],
    "nghi thai san": ["nghỉ thai sản", "trợ cấp thai sản", "chế độ thai sản"],
    "tro cap that nghiep": ["trợ cấp thất nghiệp", "BHTN", "bảo hiểm thất nghiệp"],
    "bao hiem xa hoi": ["bảo hiểm xã hội", "BHXH", "đóng BHXH", "BHXH bắt buộc"],
    "bao hiem y te": ["bảo hiểm y tế", "BHYT", "thẻ BHYT"],
    "an toan lao dong": ["an toàn lao động", "an toàn vệ sinh lao động", "ATVSLĐ"],
    "lao dong nuoc ngoai": [
        "lao động nước ngoài", "người nước ngoài làm việc tại VN", "giấy phép lao động",
    ],
    "tai nan lao dong": ["tai nạn lao động", "TNLĐ", "bệnh nghề nghiệp"],

    # === DOANH NGHIỆP / KINH DOANH ===
    "doanh nghiep": [
        "doanh nghiệp", "DN", "công ty", "thành lập doanh nghiệp",
    ],
    "thanh lap doanh nghiep": [
        "thành lập doanh nghiệp", "đăng ký kinh doanh", "đăng ký doanh nghiệp",
        "giấy chứng nhận đăng ký doanh nghiệp", "GCN ĐKKD",
    ],
    "co dong": ["cổ đông", "đại hội đồng cổ đông", "cổ tức", "cổ phần ưu đãi"],
    "von dieu le": ["vốn điều lệ", "tăng vốn điều lệ", "giảm vốn điều lệ"],
    "giai the doanh nghiep": ["giải thể doanh nghiệp", "giải thể công ty"],
    "pha san": ["phá sản", "tuyên bố phá sản", "thủ tục phá sản"],
    "dau tu nuoc ngoai": ["đầu tư nước ngoài", "FDI", "nhà đầu tư nước ngoài"],
    "ho kinh doanh": ["hộ kinh doanh", "hộ kinh doanh cá thể", "kinh doanh cá nhân"],

    # === BẤT ĐỘNG SẢN ===
    "dat dai": [
        "đất đai", "quyền sử dụng đất", "GCN QSDĐ", "sổ đỏ", "QSDĐ",
    ],
    "dat tho cu": [
        "đất thổ cư", "đất ở", "đất ở đô thị", "đất ở nông thôn",
        "Luật Đất đai", "đất phi nông nghiệp", "thổ cư",
    ],
    "dat o": [
        "đất ở", "đất thổ cư", "đất ở đô thị", "đất ở nông thôn",
    ],
    "dat nong nghiep": ["đất nông nghiệp", "đất trồng lúa", "đất trồng cây"],
    "thu hoi dat": ["thu hồi đất", "đền bù thu hồi đất", "bồi thường khi thu hồi đất"],
    "chuyen nhuong qsdd": [
        "chuyển nhượng quyền sử dụng đất", "mua bán đất",
        "hợp đồng chuyển nhượng QSDĐ",
    ],
    "so do": ["sổ đỏ", "sổ hồng", "GCN quyền sử dụng đất", "GCN QSDĐ và TS gắn liền"],
    "nha o": ["nhà ở", "sở hữu nhà", "mua bán nhà ở", "căn hộ chung cư"],
    "kinh doanh bat dong san": ["kinh doanh bất động sản", "môi giới BĐS", "sàn BĐS"],

    # === DÂN SỰ ===
    "thua ke": [
        "thừa kế", "di chúc", "thừa kế theo pháp luật",
        "thừa kế theo di chúc", "hàng thừa kế",
    ],
    "tang cho": ["tặng cho", "hợp đồng tặng cho", "tặng cho có điều kiện"],
    "boi thuong thiet hai": [
        "bồi thường thiệt hại", "bồi thường ngoài hợp đồng", "bồi thường thiệt hại do hành vi",
    ],
    "hop dong dan su": ["hợp đồng dân sự", "giao dịch dân sự", "vô hiệu hợp đồng"],
    "uy quyen": ["ủy quyền", "giấy ủy quyền", "đại diện theo ủy quyền"],
    "vay tai san": ["vay tài sản", "hợp đồng vay tài sản", "lãi suất vay"],

    # === HÔN NHÂN GIA ĐÌNH ===
    "ly hon": [
        "ly hôn", "ly hôn đơn phương", "thuận tình ly hôn",
        "đơn ly hôn", "án ly hôn",
    ],
    "ly di": [
        "ly dị", "ly hôn", "ly hôn đơn phương", "thuận tình ly hôn",
    ],
    "ket hon": ["kết hôn", "đăng ký kết hôn", "hôn thú", "giấy chứng nhận kết hôn"],
    "tai san chung": [
        "tài sản chung", "tài sản chung của vợ chồng", "phân chia tài sản chung",
        "thỏa thuận tài sản",
    ],
    "cap duong": ["cấp dưỡng", "tiền cấp dưỡng", "nghĩa vụ cấp dưỡng cho con"],
    "quyen nuoi con": ["quyền nuôi con", "giành quyền nuôi con", "quyền giám hộ"],
    "nhan con nuoi": ["nhận con nuôi", "thủ tục nhận con nuôi", "con nuôi"],

    # === HÌNH SỰ ===
    "trom cap": ["trộm cắp", "tội trộm cắp tài sản", "trộm cắp tài sản"],
    "lua dao": ["lừa đảo", "tội lừa đảo chiếm đoạt tài sản", "chiếm đoạt tài sản"],
    "co y gay thuong tich": ["cố ý gây thương tích", "cố ý đánh người"],
    "giet nguoi": ["giết người", "tội giết người", "án mạng"],
    "ma tuy": ["ma túy", "tội ma túy", "tàng trữ ma túy", "mua bán ma túy"],

    # === SỞ HỮU TRÍ TUỆ ===
    "ban quyen": ["bản quyền", "quyền tác giả", "đăng ký bản quyền", "vi phạm bản quyền"],
    "nhan hieu": [
        "nhãn hiệu", "thương hiệu", "đăng ký nhãn hiệu", "nhãn hiệu hàng hóa",
    ],
    "sang che": ["sáng chế", "đăng ký sáng chế", "patent", "giải pháp hữu ích"],
    "kieu dang cong nghiep": ["kiểu dáng công nghiệp", "đăng ký kiểu dáng"],
    "bi mat kinh doanh": ["bí mật kinh doanh", "thông tin bí mật", "trade secret"],

    # === GIÁO DỤC ===
    "trung tam ngoai ngu": [
        "trung tâm ngoại ngữ", "trung tâm hoạt động giáo dục khác",
        "cơ sở giáo dục ngoài công lập", "trung tâm thực hiện giáo dục khác",
    ],
    "giao duc dai hoc": ["giáo dục đại học", "trường đại học", "tự chủ đại học"],
    "tuyen sinh": ["tuyển sinh", "thi tuyển sinh", "tuyển sinh đại học"],

    # === HÀNH CHÍNH ===
    "khieu nai": ["khiếu nại", "đơn khiếu nại", "giải quyết khiếu nại"],
    "to cao": ["tố cáo", "đơn tố cáo", "giải quyết tố cáo"],
    "xu phat hanh chinh": [
        "xử phạt vi phạm hành chính", "xử phạt hành chính", "phạt tiền hành chính",
    ],

    # === GIAO THÔNG ===
    "vi pham giao thong": ["vi phạm giao thông", "phạt giao thông", "xử phạt giao thông"],
    "giay phep lai xe": ["giấy phép lái xe", "GPLX", "bằng lái xe"],

    # === MÔI TRƯỜNG / CARBON ===
    "moi truong": ["môi trường", "bảo vệ môi trường", "BVMT"],
    "tin chi carbon": [
        "tín chỉ carbon", "tín chỉ các-bon", "carbon credit",
        "hạn ngạch phát thải", "thị trường các-bon", "thị trường carbon",
    ],
    "san giao dich tin chi carbon": [
        "sàn giao dịch tín chỉ carbon", "sàn giao dịch tín chỉ các-bon",
        "thị trường các-bon trong nước", "phát thải khí nhà kính",
        "Luật Bảo vệ môi trường",
    ],
    "phat thai khi nha kinh": [
        "phát thải khí nhà kính", "giảm nhẹ phát thải", "khí nhà kính",
        "kiểm kê khí nhà kính", "KNK",
    ],
    "tang o-don": ["tầng ô-dôn", "bảo vệ tầng ô-dôn", "ô-dôn"],
    "rac thai": ["rác thải", "chất thải", "xử lý chất thải", "thu gom rác"],
    "o nhiem": ["ô nhiễm", "ô nhiễm môi trường", "đánh giá tác động môi trường", "ĐTM"],

    # === HÀNH CHÍNH ===
    "dang ky ho khau": ["đăng ký hộ khẩu", "sổ hộ khẩu", "đăng ký thường trú", "nhập khẩu", "tạm trú", "chuyển khẩu", "hộ khẩu thường trú"],
    "tam tru": ["tạm trú", "đăng ký tạm trú", "sổ tạm trú", "KT3", "ở trọ hợp pháp"],
    "khai sinh": ["khai sinh", "giấy khai sinh", "đăng ký khai sinh", "chứng sinh"],
    "khai tu": ["khai tử", "đăng ký khai tử", "giấy chứng tử", "xác nhận tử vong"],
    "ho tich": ["hộ tịch", "sổ hộ tịch", "đăng ký hộ tịch"],
    "quoc tich": ["quốc tịch", "nhập quốc tịch", "thôi quốc tịch", "trở lại quốc tịch", "hai quốc tịch"],
    "tiep can thong tin": ["tiếp cận thông tin", "quyền tiếp cận thông tin", "yêu cầu cung cấp thông tin nhà nước"],
    "phong chong tham nhung": ["phòng chống tham nhũng", "tham nhũng", "nhũng nhiễu", "hối lộ cán bộ", "kê khai tài sản"],

    # === LAO ĐỘNG (bổ sung) ===
    "tranh chap lao dong": ["tranh chấp lao động", "khiếu nại lao động", "kiện công ty", "đuổi việc", "sa thải trái luật"],
    "thai san": ["thai sản", "nghỉ thai sản", "chế độ thai sản", "trợ cấp sinh con", "lương thai sản"],
    "thu viec": ["thử việc", "hợp đồng thử việc", "lương thử việc", "thời gian thử việc"],
    "bao hiem that nghiep": ["bảo hiểm thất nghiệp", "BHTN", "trợ cấp thất nghiệp", "hỗ trợ tìm việc"],

    # === BẢO HIỂM XÃ HỘI (bổ sung) ===
    "rut bao hiem": ["rút BHXH một lần", "nhận BHXH một lần", "rút sổ bảo hiểm", "hoàn trả BHXH"],
    "rut bhxh": ["rút BHXH một lần", "rút bảo hiểm xã hội một lần", "nhận BHXH một lần"],
    "truoc ba": ["lệ phí trước bạ", "thuế trước bạ", "trước bạ xe", "trước bạ nhà đất"],
    "thue truoc ba": ["thuế trước bạ", "lệ phí trước bạ", "trước bạ xe", "trước bạ nhà đất"],
    "luong huu": ["lương hưu", "nghỉ hưu", "tuổi hưu", "chế độ hưu trí", "mức hưởng lương hưu"],

    # === THUẾ (bổ sung) ===
    "le phi truoc ba": ["lệ phí trước bạ", "trước bạ xe", "trước bạ nhà đất", "thuế trước bạ"],
    "thue su dung dat": ["thuế sử dụng đất", "thuế đất", "thuế nhà đất", "thuế sử dụng đất phi nông nghiệp"],

    # === DOANH NGHIỆP (bổ sung) ===
    "gop von": ["góp vốn", "góp vốn điều lệ", "chuyển nhượng vốn", "tăng vốn điều lệ"],
    "hop dong kinh doanh": ["hợp đồng kinh doanh", "hợp đồng thương mại", "hợp đồng mua bán", "vi phạm hợp đồng", "phạt vi phạm hợp đồng"],

    # === BẤT ĐỘNG SẢN (bổ sung) ===
    "mua ban nha": ["mua bán nhà", "hợp đồng mua bán nhà", "chuyển nhượng nhà", "mua nhà trả góp"],
    "thue nha": ["thuê nhà", "cho thuê nhà", "hợp đồng thuê nhà", "tiền cọc thuê nhà", "thuê căn hộ"],
    "cap so do": ["cấp sổ đỏ", "sổ hồng", "giấy chứng nhận quyền sử dụng đất", "GCNQSDĐ"],
    "tranh chap dat dai": ["tranh chấp đất đai", "tranh chấp đất", "khiếu nại đất đai", "lấn chiếm đất", "ranh giới đất"],
    "xay dung nha": ["xây dựng nhà", "giấy phép xây dựng", "xây nhà không phép", "vi phạm xây dựng"],
    "cho thue mat bang": ["cho thuê mặt bằng", "cho thuê mặt bằng kinh doanh", "hợp đồng thuê mặt bằng thương mại"],
    "chung cu": ["chung cư", "nhà chung cư", "ban quản trị chung cư", "phí dịch vụ chung cư", "tranh chấp chung cư"],

    # === HÔN NHÂN (bổ sung) ===
    "tai san vo chong": ["tài sản vợ chồng", "tài sản chung vợ chồng", "tài sản riêng", "phân chia tài sản khi ly hôn", "hôn ước"],
    "bao luc gia dinh": ["bạo lực gia đình", "bạo hành gia đình", "bạo lực vợ chồng"],
    "hon nhan dong gioi": ["hôn nhân đồng giới", "kết hôn đồng giới", "hôn nhân LGBT", "pháp luật đồng tính"],

    # === HÌNH SỰ (bổ sung) ===
    "tai nan giao thong": ["tai nạn giao thông", "lỗi gây tai nạn", "bồi thường tai nạn xe"],
    "tam giam": ["tạm giam", "tạm giữ", "bắt tạm giam", "thời hạn tạm giam", "gia hạn tạm giam"],

    # === DÂN SỰ (bổ sung) ===
    "di chuc": ["di chúc", "lập di chúc", "di chúc hợp pháp", "công chứng di chúc"],
    "hop dong vay no": ["hợp đồng vay nợ", "hợp đồng vay tiền", "đòi nợ", "lãi suất cho vay", "nợ xấu cá nhân", "vay không trả"],
    "bao dam nghia vu": ["bảo đảm nghĩa vụ", "thế chấp", "cầm cố", "bảo lãnh", "đặt cọc", "ký cược"],
    "quyen nhan than": ["quyền nhân thân", "quyền hình ảnh", "xúc phạm danh dự nhân phẩm", "bồi thường danh dự"],
    "cong chung": ["công chứng", "công chứng hợp đồng", "văn phòng công chứng", "công chứng viên", "chứng thực"],

    # === GIÁO DỤC (bổ sung) ===
    "hoc phi": ["học phí", "miễn giảm học phí", "học bổng", "phí giáo dục"],
    "truong tu thuc": ["trường tư thục", "trường ngoài công lập", "trường dân lập", "cơ sở giáo dục tư nhân"],
    "diem thi": ["điểm thi", "thi tốt nghiệp", "tuyển sinh đại học", "điểm chuẩn", "gian lận thi cử"],

    # === SỞ HỮU TRÍ TUỆ (bổ sung) ===
    "hang gia": ["hàng giả", "hàng nhái", "hàng kém chất lượng", "làm hàng giả"],

    # === TÀI CHÍNH NGÂN HÀNG ===
    "vay ngan hang": ["vay ngân hàng", "vay vốn ngân hàng", "cho vay tín dụng", "hợp đồng tín dụng", "lãi suất ngân hàng"],
    "the chap nha": ["thế chấp nhà", "thế chấp tài sản", "thế chấp nhà đất", "vay thế chấp", "giải chấp"],
    "xu ly no xau": ["nợ xấu", "xử lý nợ xấu", "VAMC", "thu hồi nợ", "siết nợ"],
    "chung khoan": ["chứng khoán", "cổ phiếu", "trái phiếu", "giao dịch chứng khoán", "thị trường chứng khoán", "HOSE", "HNX"],

    # === MÔI TRƯỜNG (bổ sung) ===
    "khai thac khoang san": ["khai thác khoáng sản", "giấy phép khai thác", "cát sỏi", "than đá", "quặng"],
    "tai nguyen nuoc": ["tài nguyên nước", "khai thác nước ngầm", "sử dụng tài nguyên nước"],

    # === GIAO THÔNG (bổ sung) ===
    "bang lai xe": ["bằng lái xe", "giấy phép lái xe", "thi bằng lái", "GPLX", "thu hồi bằng lái"],
    "dang ky xe": ["đăng ký xe", "đăng ký xe máy", "đăng ký ô tô", "sang tên xe", "chuyển nhượng xe"],

    # === Y TẾ ===
    "kham chua benh": ["khám chữa bệnh", "quyền bệnh nhân", "chứng chỉ hành nghề y", "bệnh viện tư nhân"],
    "duoc pham": ["dược phẩm", "thuốc", "giấy phép kinh doanh dược", "nhà thuốc", "thuốc kê đơn"],
    "thuc pham": ["thực phẩm", "vệ sinh an toàn thực phẩm", "ngộ độc thực phẩm", "giấy phép ATTP"],

    # === XUẤT NHẬP KHẨU ===
    "xuat khau": ["xuất khẩu", "xuất khẩu hàng hóa", "thủ tục xuất khẩu", "C/O", "giấy chứng nhận xuất xứ"],
    "hai quan": ["hải quan", "thủ tục hải quan", "khai báo hải quan", "kiểm tra hải quan", "thuế hải quan"],
    "nhap khau": ["nhập khẩu", "nhập khẩu hàng hóa", "quota nhập khẩu", "hàng cấm nhập khẩu", "giấy phép nhập khẩu"],

    # === KHÁC ===
    "con heo": ["con heo", "con lợn", "lợn", "chăn nuôi lợn", "thú y"],
    "phong chay chua chay": ["phòng cháy chữa cháy", "PCCC", "an toàn cháy nổ"],
}

# Lĩnh vực → list văn bản chung (Bộ luật, Luật khung) cần liên kết
CROSS_LAW_MAPPING: dict[str, list[dict]] = {
    "thuế": [
        {"name": "Bộ luật Dân sự 2015", "ref": "Toàn bộ", "note": "Nghĩa vụ tài sản, hợp đồng cơ sở của quan hệ thuế"},
        {"name": "Luật Quản lý thuế 2019", "ref": "Toàn bộ", "note": "Thủ tục khai báo, hoàn thuế, cưỡng chế"},
        {"name": "Bộ luật Hình sự 2015 (sửa đổi 2017)", "ref": "Điều 200", "note": "Tội trốn thuế — hình phạt tù"},
    ],
    "lao động": [
        {"name": "Bộ luật Lao động 2019", "ref": "Toàn bộ", "note": "Khung pháp lý chính của quan hệ lao động"},
        {"name": "Bộ luật Dân sự 2015", "ref": "Hợp đồng", "note": "Áp dụng nguyên tắc hợp đồng khi BLLĐ không quy định"},
        {"name": "Luật BHXH 2014 (sửa đổi 2024)", "ref": "Toàn bộ", "note": "Nghĩa vụ đóng BHXH bắt buộc"},
        {"name": "Bộ luật Hình sự 2015", "ref": "Điều 214-216", "note": "Tội liên quan BHXH, BHYT"},
    ],
    "kinh doanh": [
        {"name": "Luật Doanh nghiệp 2020", "ref": "Toàn bộ", "note": "Khung pháp lý DN, cơ cấu, quản trị"},
        {"name": "Bộ luật Dân sự 2015", "ref": "Hợp đồng, đại diện", "note": "Cơ sở giao dịch dân sự"},
        {"name": "Luật Đầu tư 2020", "ref": "Toàn bộ", "note": "Điều kiện đầu tư, ngành nghề kinh doanh có ĐK"},
        {"name": "Luật Thương mại 2005", "ref": "Toàn bộ", "note": "Hoạt động thương mại"},
    ],
    "bất động sản": [
        {"name": "Luật Đất đai 2024", "ref": "Toàn bộ", "note": "Quyền sử dụng đất, thu hồi, đền bù"},
        {"name": "Luật Nhà ở 2023", "ref": "Toàn bộ", "note": "Sở hữu, giao dịch nhà ở"},
        {"name": "Bộ luật Dân sự 2015", "ref": "Quyền sở hữu, hợp đồng", "note": "Nguyên tắc giao dịch tài sản"},
        {"name": "Luật Kinh doanh BĐS 2023", "ref": "Toàn bộ", "note": "Hoạt động kinh doanh BĐS"},
    ],
    "hình sự": [
        {"name": "Bộ luật Hình sự 2015 (sửa đổi 2017)", "ref": "Toàn bộ", "note": "Tội phạm và hình phạt"},
        {"name": "Bộ luật Tố tụng Hình sự 2015 (sửa đổi 2021)", "ref": "Toàn bộ", "note": "Trình tự điều tra, truy tố, xét xử"},
    ],
    "dân sự": [
        {"name": "Bộ luật Dân sự 2015", "ref": "Toàn bộ", "note": "Quyền dân sự, hợp đồng, thừa kế"},
        {"name": "Bộ luật Tố tụng Dân sự 2015 (sửa đổi 2020)", "ref": "Toàn bộ", "note": "Trình tự giải quyết tranh chấp dân sự"},
    ],
    "hôn nhân": [
        {"name": "Luật Hôn nhân và Gia đình 2014", "ref": "Toàn bộ", "note": "Khung pháp lý kết hôn, ly hôn, con chung"},
        {"name": "Bộ luật Dân sự 2015", "ref": "Tài sản chung", "note": "Phân chia tài sản"},
    ],
    "sở hữu trí tuệ": [
        {"name": "Luật Sở hữu Trí tuệ 2005 (sửa đổi 2022)", "ref": "Toàn bộ", "note": "Bản quyền, nhãn hiệu, sáng chế"},
        {"name": "Bộ luật Dân sự 2015", "ref": "Quyền tác giả", "note": "Nguyên tắc chung"},
        {"name": "Bộ luật Hình sự 2015", "ref": "Điều 225-226", "note": "Tội xâm phạm SHTT"},
    ],
    "giáo dục": [
        {"name": "Luật Giáo dục 2019", "ref": "Toàn bộ", "note": "Khung hệ thống giáo dục quốc dân"},
        {"name": "Luật Giáo dục Đại học 2012 (sửa đổi 2018)", "ref": "Toàn bộ", "note": "GDĐH, tự chủ"},
    ],
    "môi trường": [
        {"name": "Luật Bảo vệ môi trường 2020", "ref": "Toàn bộ", "note": "Khung BVMT, Điều 139 — thị trường các-bon trong nước"},
        {"name": "Nghị định 06/2022/NĐ-CP", "ref": "Toàn bộ", "note": "Giảm nhẹ phát thải khí nhà kính + bảo vệ tầng ô-dôn"},
        {"name": "Quyết định 232/QĐ-TTg/2025", "ref": "Toàn bộ", "note": "Đề án phát triển thị trường các-bon (lộ trình thí điểm 2025, vận hành 2028)"},
        {"name": "Luật Đa dạng sinh học 2008", "ref": "Toàn bộ", "note": "Bảo vệ ĐDSH"},
    ],
    "hành chính": [
        {"name": "Luật Cư trú 2020", "ref": "Toàn bộ", "note": "Đăng ký thường trú, tạm trú, hộ khẩu"},
        {"name": "Luật Hộ tịch 2014", "ref": "Toàn bộ", "note": "Khai sinh, kết hôn, khai tử, hộ tịch"},
        {"name": "Luật Quốc tịch Việt Nam 2008", "ref": "Toàn bộ", "note": "Nhập, thôi, trở lại quốc tịch"},
        {"name": "Luật Xử lý vi phạm hành chính 2012 (sửa đổi 2020, 2025)", "ref": "Toàn bộ", "note": "Phạt hành chính, cưỡng chế"},
        {"name": "Luật Khiếu nại 2011, Luật Tố cáo 2018", "ref": "Toàn bộ", "note": "Trình tự khiếu nại, tố cáo"},
    ],
    "bảo hiểm xã hội": [
        {"name": "Luật Bảo hiểm xã hội 2014 (sửa đổi 2024)", "ref": "Toàn bộ", "note": "Đóng/hưởng BHXH, hưu trí, thai sản"},
        {"name": "Luật Bảo hiểm y tế 2008 (sửa đổi)", "ref": "Toàn bộ", "note": "Thẻ BHYT, đồng chi trả"},
        {"name": "Luật Việc làm 2013", "ref": "Toàn bộ", "note": "Bảo hiểm thất nghiệp, hỗ trợ tìm việc"},
        {"name": "Bộ luật Lao động 2019", "ref": "Liên quan BHXH", "note": "Nghĩa vụ đóng BHXH bắt buộc"},
    ],
    "tài chính ngân hàng": [
        {"name": "Luật Các tổ chức tín dụng 2024", "ref": "Toàn bộ", "note": "Hoạt động ngân hàng, vay vốn, thế chấp, xử lý nợ xấu"},
        {"name": "Luật Chứng khoán 2019", "ref": "Toàn bộ", "note": "Phát hành, niêm yết, giao dịch CK"},
        {"name": "Bộ luật Dân sự 2015", "ref": "Phần Bảo đảm thực hiện nghĩa vụ", "note": "Thế chấp, cầm cố, bảo lãnh"},
        {"name": "Bộ luật Hình sự 2015", "ref": "Điều 353-360", "note": "Tội liên quan tài chính ngân hàng"},
    ],
    "giao thông": [
        {"name": "Luật Trật tự, an toàn giao thông đường bộ 2024", "ref": "Toàn bộ", "note": "Quy tắc giao thông, vi phạm, xử phạt"},
        {"name": "Luật Đường bộ 2024", "ref": "Toàn bộ", "note": "Hạ tầng đường bộ, kinh doanh vận tải"},
        {"name": "Bộ luật Hình sự 2015", "ref": "Điều 260-266", "note": "Tội vi phạm an toàn giao thông"},
    ],
    "y tế": [
        {"name": "Luật Khám bệnh, chữa bệnh 2023", "ref": "Toàn bộ", "note": "Hành nghề y, quyền bệnh nhân"},
        {"name": "Luật Dược 2016 (sửa đổi 2024)", "ref": "Toàn bộ", "note": "Quản lý thuốc, kinh doanh dược"},
        {"name": "Luật An toàn thực phẩm 2010", "ref": "Toàn bộ", "note": "VSATTP, ngộ độc thực phẩm"},
    ],
    "xuất nhập khẩu": [
        {"name": "Luật Hải quan 2014", "ref": "Toàn bộ", "note": "Thủ tục hải quan, kiểm tra"},
        {"name": "Luật Quản lý ngoại thương 2017", "ref": "Toàn bộ", "note": "Xuất khẩu, nhập khẩu, quota"},
        {"name": "Luật Thuế xuất khẩu, thuế nhập khẩu 2016", "ref": "Toàn bộ", "note": "Thuế XNK"},
    ],
}

# Heuristic xác định domain từ query
_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "thuế": [
        "thu nhap chiu thue", "tncn", "tndn", "gtgt", "vat",
        "thue thu nhap", "thue gia tri", "thue tieu thu", "thue nha thau",
        "tron thue", "hoan thue", "quyet toan thue", "thue truoc ba",
        "thue su dung dat", "le phi truoc ba", "ke khai thue",
        # KHÔNG dùng "thue" trần — dễ collide với "thuê" (rent)
    ],
    "lao động": [
        "lao dong", "hdld", "hop dong lao dong", "sa thai", "tien luong",
        "ky luat", "nghi viec", "nghi phep",
        "lam them gio", "tang ca", "phu cap", "luong toi thieu",
        "tnld", "tai nan lao dong", "an toan lao dong",
        "tien luong",
    ],
    "kinh doanh": ["doanh nghiep", "cong ty", "kinh doanh", "dau tu", "co dong"],
    "bất động sản": [
        "bat dong san", "dat dai", "nha o", "so do", "so hong",
        "quyen su dung dat", "chuyen nhuong",
        "dat tho cu", "dat o", "dat nong nghiep", "dat phi nong nghiep",
        "tho cu", "thu hoi dat", "den bu dat", "gcn qsdd", "qsdd",
        "chung cu", "mua ban nha", "thue nha", "cho thue mat bang",
        "xay dung nha", "giay phep xay dung", "tranh chap dat dai",
    ],
    "hình sự": [
        "hinh su", "toi pham", "hinh phat", "tu hinh", "phat tu",
        "trom cap", "lua dao", "co y gay thuong tich", "giet nguoi",
        "ma tuy", "danh bac", "tham o", "xam pham", "cuop tai san",
        "tam giam", "tam giu", "bat tam giam", "an mang", "thuong tich",
    ],
    "dân sự": ["dan su", "thua ke", "tang cho", "boi thuong"],
    "hôn nhân": [
        "ly hon", "ly di", "ket hon", "hon nhan", "tai san chung",
        "con chung", "cap duong", "quyen nuoi con", "nhan con nuoi",
        "bao luc gia dinh", "bao hanh gia dinh", "bao luc vo chong",
        "tai san vo chong", "hon uoc", "dong gioi",
    ],
    "sở hữu trí tuệ": ["so huu tri tue", "ban quyen", "nhan hieu",
                         "sang che", "kieu dang"],
    "giáo dục": [
        "giao duc", "truong hoc", "trung tam ngoai ngu", "dao tao",
        "hoc phi", "diem chuan", "diem thi", "tuyen sinh", "thi tot nghiep",
        "truong tu thuc", "truong dai hoc", "gian lan thi cu",
    ],
    "môi trường": [
        "moi truong", "bao ve moi truong", "bvmt",
        "carbon", "tin chi carbon", "tin chi cac-bon", "carbon credit",
        "san giao dich tin chi carbon", "thi truong cac-bon", "thi truong carbon",
        "phat thai", "khi nha kinh", "knk", "giam nhe phat thai",
        "tang o-don", "tang ozon", "rac thai", "chat thai", "o nhiem",
        "danh gia tac dong moi truong", "dtm", "bien doi khi hau",
        "khai thac khoang san", "khoang san", "tai nguyen nuoc", "nuoc ngam",
    ],
    "hành chính": [
        "hanh chinh", "ho khau", "ho tich", "khai sinh", "khai tu",
        "tam tru", "thuong tru", "kt3", "quoc tich",
        "khieu nai", "to cao", "xu phat hanh chinh",
        "tham nhung", "tiep can thong tin", "kham xet",
    ],
    "bảo hiểm xã hội": [
        "bhxh", "bao hiem xa hoi", "bao hiem y te", "bhyt",
        "luong huu", "huu tri", "rut bao hiem", "rut bhxh",
        "tro cap that nghiep", "bhtn", "thai san", "om dau",
    ],
    "tài chính ngân hàng": [
        "tai chinh", "ngan hang", "vay ngan hang", "tin dung",
        "the chap", "no xau", "vamc", "lai suat",
        "chung khoan", "co phieu", "trai phieu", "hose", "hnx",
    ],
    "giao thông": [
        "giao thong", "vi pham giao thong", "bang lai xe", "gplx",
        "dang ky xe", "phat nguoi", "nong do con", "vuot den do",
        "tai nan giao thong", "an toan giao thong",
    ],
    "y tế": [
        "y te", "kham chua benh", "benh vien", "duoc pham", "thuoc",
        "thuc pham", "an toan thuc pham", "vsattp", "ngo doc thuc pham",
        "hanh nghe y", "bac si",
    ],
    "xuất nhập khẩu": [
        "xuat khau", "nhap khau", "xnk", "hai quan",
        "co quy tac xuat xu", "ngoai thuong", "quota",
        "thue xuat khau", "thue nhap khau",
    ],
}


_DOC_TYPE_PREFIXES = (
    "luat", "bo luat", "phap lenh", "nghi quyet", "nghi dinh",
    "thong tu", "quyet dinh", "chi thi", "cong van", "huong dan",
)

# Topic (normalized, không dấu) → tên Luật/Bộ luật gốc chính xác.
# Thêm như là search keyword để surface Luật gốc khi tên Luật khác hẳn topic
# (vd. "ly hôn" → "Luật Hôn nhân và Gia đình").
PARENT_LAW_MAPPING: dict[str, list[str]] = {
    "ly hon": ["Luật Hôn nhân và Gia đình"],
    "ly di": ["Luật Hôn nhân và Gia đình"],
    "ket hon": ["Luật Hôn nhân và Gia đình"],
    "tai san chung": ["Luật Hôn nhân và Gia đình", "Bộ luật Dân sự"],
    "thua ke": ["Bộ luật Dân sự"],
    "tang cho": ["Bộ luật Dân sự"],
    "boi thuong thiet hai": ["Bộ luật Dân sự"],
    "hop dong lao dong": ["Bộ luật Lao động"],
    "sa thai": ["Bộ luật Lao động"],
    "tien luong": ["Bộ luật Lao động"],
    "ky luat lao dong": ["Bộ luật Lao động"],
    "lam them gio": ["Bộ luật Lao động"],
    "tang ca": ["Bộ luật Lao động"],
    "nghi phep": ["Bộ luật Lao động"],
    "nghi om": ["Bộ luật Lao động", "Luật Bảo hiểm xã hội"],
    "nghi thai san": ["Bộ luật Lao động", "Luật Bảo hiểm xã hội"],
    "tai nan lao dong": ["Bộ luật Lao động", "Luật An toàn vệ sinh lao động"],
    "an toan lao dong": ["Luật An toàn vệ sinh lao động"],
    "tro cap that nghiep": ["Luật Việc làm", "Luật Bảo hiểm xã hội"],
    "moi truong": ["Luật Bảo vệ môi trường"],
    "tin chi carbon": ["Luật Bảo vệ môi trường", "Nghị định 06/2022"],
    "san giao dich tin chi carbon": [
        "Luật Bảo vệ môi trường", "Nghị định 06/2022",
        "thị trường các-bon",
    ],
    "phat thai khi nha kinh": [
        "Luật Bảo vệ môi trường", "Nghị định 06/2022 phát thải",
    ],
    "tang o-don": ["Luật Bảo vệ môi trường", "Nghị định 06/2022 tầng ô-dôn"],
    "rac thai": ["Luật Bảo vệ môi trường"],
    "o nhiem": ["Luật Bảo vệ môi trường"],
    "bao hiem xa hoi": ["Luật Bảo hiểm xã hội"],
    "bao hiem y te": ["Luật Bảo hiểm y tế"],
    "thue thu nhap ca nhan": ["Luật Thuế thu nhập cá nhân"],
    "thue gia tri gia tang": ["Luật Thuế giá trị gia tăng"],
    "thue thu nhap doanh nghiep": ["Luật Thuế thu nhập doanh nghiệp"],
    "quan ly thue": ["Luật Quản lý thuế"],
    "doanh nghiep": ["Luật Doanh nghiệp"],
    "dau tu": ["Luật Đầu tư"],
    "dat dai": ["Luật Đất đai"],
    "dat tho cu": ["Luật Đất đai"],
    "dat o": ["Luật Đất đai"],
    "dat nong nghiep": ["Luật Đất đai"],
    "thu hoi dat": ["Luật Đất đai"],
    "chuyen nhuong qsdd": ["Luật Đất đai", "Bộ luật Dân sự"],
    "so do": ["Luật Đất đai"],
    "nha o": ["Luật Nhà ở"],
    "kinh doanh bat dong san": ["Luật Kinh doanh bất động sản"],
    "toi pham": ["Bộ luật Hình sự"],
    "trom cap": ["Bộ luật Hình sự"],
    "lua dao": ["Bộ luật Hình sự"],
    "ban quyen": ["Luật Sở hữu trí tuệ"],
    "nhan hieu": ["Luật Sở hữu trí tuệ"],
    "sang che": ["Luật Sở hữu trí tuệ"],
    "trung tam ngoai ngu": ["Luật Giáo dục"],
    "giao duc dai hoc": ["Luật Giáo dục đại học"],
    "hoc phi": ["Luật Giáo dục"],
    "truong tu thuc": ["Luật Giáo dục"],
    "diem thi": ["Luật Giáo dục"],

    # Hành chính
    "dang ky ho khau": ["Luật Cư trú"],
    "tam tru": ["Luật Cư trú"],
    "khai sinh": ["Luật Hộ tịch"],
    "khai tu": ["Luật Hộ tịch"],
    "ho tich": ["Luật Hộ tịch"],
    "quoc tich": ["Luật Quốc tịch"],
    "tiep can thong tin": ["Luật Tiếp cận thông tin"],
    "phong chong tham nhung": ["Luật Phòng chống tham nhũng"],
    "xu phat hanh chinh": ["Luật Xử lý vi phạm hành chính"],
    "khieu nai": ["Luật Khiếu nại"],
    "to cao": ["Luật Tố cáo"],

    # Lao động bổ sung
    "tranh chap lao dong": ["Bộ luật Lao động"],
    "thai san": ["Bộ luật Lao động", "Luật Bảo hiểm xã hội"],
    "thu viec": ["Bộ luật Lao động"],
    "bao hiem that nghiep": ["Luật Việc làm", "Luật Bảo hiểm xã hội"],

    # BHXH bổ sung
    "rut bao hiem": ["Luật Bảo hiểm xã hội"],
    "rut bhxh": ["Luật Bảo hiểm xã hội"],
    "luong huu": ["Luật Bảo hiểm xã hội"],
    "truoc ba": ["Luật Phí và Lệ phí"],
    "thue truoc ba": ["Luật Phí và Lệ phí"],

    # Thuế bổ sung
    "le phi truoc ba": ["Luật Phí và Lệ phí"],
    "thue su dung dat": ["Luật Thuế sử dụng đất phi nông nghiệp"],
    "thue tieu thu dac biet": ["Luật Thuế tiêu thụ đặc biệt"],
    "thue xuat nhap khau": ["Luật Thuế xuất khẩu, thuế nhập khẩu"],

    # Doanh nghiệp bổ sung
    "thanh lap doanh nghiep": ["Luật Doanh nghiệp"],
    "giai the doanh nghiep": ["Luật Doanh nghiệp"],
    "pha san": ["Luật Phá sản"],
    "gop von": ["Luật Doanh nghiệp"],
    "hop dong kinh doanh": ["Luật Thương mại", "Bộ luật Dân sự"],
    "co dong": ["Luật Doanh nghiệp"],
    "von dieu le": ["Luật Doanh nghiệp"],

    # BĐS bổ sung
    "mua ban nha": ["Luật Nhà ở", "Luật Kinh doanh bất động sản"],
    "thue nha": ["Luật Nhà ở"],
    "cap so do": ["Luật Đất đai"],
    "tranh chap dat dai": ["Luật Đất đai"],
    "xay dung nha": ["Luật Xây dựng"],
    "cho thue mat bang": ["Luật Kinh doanh bất động sản"],
    "chung cu": ["Luật Nhà ở"],

    # Hôn nhân bổ sung
    "tai san vo chong": ["Luật Hôn nhân và Gia đình"],
    "bao luc gia dinh": ["Luật Phòng chống bạo lực gia đình"],
    "hon nhan dong gioi": ["Luật Hôn nhân và Gia đình"],
    "cap duong": ["Luật Hôn nhân và Gia đình"],
    "quyen nuoi con": ["Luật Hôn nhân và Gia đình"],
    "nhan con nuoi": ["Luật Nuôi con nuôi"],

    # Hình sự bổ sung
    "tai nan giao thong": ["Bộ luật Hình sự", "Bộ luật Dân sự"],
    "tam giam": ["Luật Thi hành tạm giữ tạm giam"],
    "co y gay thuong tich": ["Bộ luật Hình sự"],
    "giet nguoi": ["Bộ luật Hình sự"],
    "ma tuy": ["Bộ luật Hình sự", "Luật Phòng chống ma túy"],

    # Dân sự bổ sung
    "di chuc": ["Bộ luật Dân sự"],
    "hop dong vay no": ["Bộ luật Dân sự"],
    "bao dam nghia vu": ["Bộ luật Dân sự"],
    "quyen nhan than": ["Bộ luật Dân sự"],
    "cong chung": ["Luật Công chứng"],
    "uy quyen": ["Bộ luật Dân sự"],
    "vay tai san": ["Bộ luật Dân sự"],
    "tang cho": ["Bộ luật Dân sự"],

    # SHTT bổ sung
    "hang gia": ["Luật Sở hữu trí tuệ", "Bộ luật Hình sự"],
    "kieu dang cong nghiep": ["Luật Sở hữu trí tuệ"],
    "bi mat kinh doanh": ["Luật Sở hữu trí tuệ"],

    # Tài chính ngân hàng
    "vay ngan hang": ["Luật Các tổ chức tín dụng"],
    "the chap nha": ["Luật Các tổ chức tín dụng", "Bộ luật Dân sự"],
    "xu ly no xau": ["Luật Các tổ chức tín dụng"],
    "chung khoan": ["Luật Chứng khoán"],

    # Môi trường bổ sung
    "khai thac khoang san": ["Luật Khoáng sản"],
    "tai nguyen nuoc": ["Luật Tài nguyên nước"],

    # Giao thông
    "bang lai xe": ["Luật Trật tự an toàn giao thông đường bộ"],
    "vi pham giao thong": ["Luật Trật tự an toàn giao thông đường bộ"],
    "dang ky xe": ["Luật Trật tự an toàn giao thông đường bộ"],
    "giay phep lai xe": ["Luật Trật tự an toàn giao thông đường bộ"],

    # Y tế
    "kham chua benh": ["Luật Khám bệnh chữa bệnh"],
    "duoc pham": ["Luật Dược"],
    "thuc pham": ["Luật An toàn thực phẩm"],

    # Xuất nhập khẩu
    "xuat khau": ["Luật Quản lý ngoại thương"],
    "hai quan": ["Luật Hải quan"],
    "nhap khau": ["Luật Quản lý ngoại thương"],
}


def expand_keywords(query: str) -> list[str]:
    """Trả list keywords để search song song. Bao gồm:
      - query gốc
      - tên Luật gốc đã biết từ PARENT_LAW_MAPPING (ưu tiên cao nhất)
      - "Luật <query>" fallback
      - synonyms từ SYNONYM_MAPPING
    """
    nq = normalize_vi(query).strip()
    out = [query.strip()]
    seen = {nq}

    # 1. Parent law mapping — chính xác nhất
    parent_added = False
    for key, parents in PARENT_LAW_MAPPING.items():
        if key in nq or nq in key:
            for p in parents:
                np = normalize_vi(p)
                if np not in seen:
                    seen.add(np)
                    out.append(p)
                    parent_added = True

    # 2. Fallback: "Luật <query>" nếu chưa có parent
    if not parent_added and not any(nq.startswith(p) for p in _DOC_TYPE_PREFIXES):
        candidate = f"Luật {query.strip()}"
        nc = normalize_vi(candidate)
        if nc not in seen:
            seen.add(nc)
            out.append(candidate)

    # 3. Synonyms
    for key, syns in SYNONYM_MAPPING.items():
        if key in nq or nq in key:
            for s in syns:
                ns = normalize_vi(s)
                if ns not in seen:
                    seen.add(ns)
                    out.append(s)
    return out[:5]


def detect_domain(query: str) -> str:
    """Trả domain key. Default 'dân sự' nếu không match."""
    nq = normalize_vi(query)
    best = None
    best_hits = 0
    for domain, kws in _DOMAIN_KEYWORDS.items():
        hits = sum(1 for k in kws if k in nq)
        if hits > best_hits:
            best = domain
            best_hits = hits
    return best or "dân sự"


def get_cross_laws(domain: str) -> list[dict]:
    return CROSS_LAW_MAPPING.get(domain, [])


def analyze(query: str) -> dict:
    """One-shot: trả keywords mở rộng + domain + cross-laws."""
    domain = detect_domain(query)
    return {
        "query": query,
        "expanded_keywords": expand_keywords(query),
        "domain": domain,
        "cross_laws": get_cross_laws(domain),
    }


if __name__ == "__main__":
    for q in [
        "thuế thu nhập cá nhân",
        "sa thải công nhân",
        "ly hôn đơn phương",
        "trung tâm ngoại ngữ phải xin giấy phép gì",
    ]:
        a = analyze(q)
        print(f"\n=== {q!r} ===")
        print(f"  domain: {a['domain']}")
        print(f"  expanded: {a['expanded_keywords']}")
        print(f"  cross-laws ({len(a['cross_laws'])}): {[c['name'] for c in a['cross_laws']]}")
