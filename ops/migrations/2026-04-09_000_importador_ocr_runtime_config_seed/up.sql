BEGIN;

-- Ensure the unique constraint exists (may be missing if imp_config was pre-created).
CREATE UNIQUE INDEX IF NOT EXISTS uq_imp_config_module_key ON imp_config (module, key);

-- Runtime OCR config for importador.
-- This migrates the in-code defaults into imp_config so DB becomes the source of truth.
INSERT INTO imp_config (id, module, key, value_text, value_list, label) VALUES
    (gen_random_uuid(), 'ocr_config', 'min_width', '1800', NULL, 'OCR minimum width'),
    (gen_random_uuid(), 'ocr_config', 'weak_text_min_words', '4', NULL, 'Weak text minimum words'),
    (gen_random_uuid(), 'ocr_config', 'weak_text_min_chars', '24', NULL, 'Weak text minimum chars'),
    (gen_random_uuid(), 'ocr_config', 'pdf_render_dpi', '300', NULL, 'PDF render DPI'),
    (gen_random_uuid(), 'ocr_config', 'image_contrast', '1.8', NULL, 'Image contrast'),
    (gen_random_uuid(), 'ocr_config', 'image_sharpness', '2.0', NULL, 'Image sharpness'),
    (gen_random_uuid(), 'ocr_config', 'tesseract_languages', NULL, '["spa","eng"]'::jsonb, 'Tesseract languages'),
    (gen_random_uuid(), 'ocr_config', 'primary_psm_modes', NULL, '["6","11"]'::jsonb, 'Primary PSM modes'),
    (gen_random_uuid(), 'ocr_config', 'rescue_psm_modes', NULL, '["6"]'::jsonb, 'Rescue PSM modes'),
    (gen_random_uuid(), 'ocr_config', 'small_rotation_angles', NULL, '["-4","-2","2","4"]'::jsonb, 'Small rotation angles'),
    (gen_random_uuid(), 'ocr_config', 'primary_variant_labels', NULL, '["base","base_rot-2","base_rot+2","perspective","perspective_rot-2","perspective_rot+2","autocontrast","autocontrast_rot-2","autocontrast_rot+2","threshold","trimmed","trimmed_rot90"]'::jsonb, 'Primary OCR variant labels'),
    (gen_random_uuid(), 'ocr_config', 'median_filter_size', '3', NULL, 'Median filter size'),
    (gen_random_uuid(), 'ocr_config', 'perspective_threshold_value', '165', NULL, 'Perspective threshold value'),
    (gen_random_uuid(), 'ocr_config', 'threshold_value', '170', NULL, 'Threshold value'),
    (gen_random_uuid(), 'ocr_config', 'threshold_low_value', '140', NULL, 'Threshold low value'),
    (gen_random_uuid(), 'ocr_config', 'trim_background_threshold', '245', NULL, 'Trim background threshold'),
    (gen_random_uuid(), 'ocr_config', 'trim_min_crop_ratio', '0.35', NULL, 'Trim min crop ratio'),
    (gen_random_uuid(), 'ocr_config', 'trim_padding_ratio', '0.03', NULL, 'Trim padding ratio'),
    (gen_random_uuid(), 'ocr_config', 'trim_min_padding_px', '8', NULL, 'Trim min padding px'),
    (gen_random_uuid(), 'ocr_config', 'perspective_canny_threshold1', '60', NULL, 'Perspective Canny threshold1'),
    (gen_random_uuid(), 'ocr_config', 'perspective_canny_threshold2', '180', NULL, 'Perspective Canny threshold2'),
    (gen_random_uuid(), 'ocr_config', 'perspective_blur_kernel', '5', NULL, 'Perspective blur kernel'),
    (gen_random_uuid(), 'ocr_config', 'perspective_kernel_size', '5', NULL, 'Perspective kernel size'),
    (gen_random_uuid(), 'ocr_config', 'perspective_min_area_ratio', '0.18', NULL, 'Perspective min area ratio'),
    (gen_random_uuid(), 'ocr_config', 'perspective_min_output_ratio', '0.35', NULL, 'Perspective min output ratio'),
    (gen_random_uuid(), 'ocr_config', 'easyocr_languages', NULL, '["es","en"]'::jsonb, 'EasyOCR languages'),
    (gen_random_uuid(), 'ocr_config', 'easyocr_gpu', 'false', NULL, 'EasyOCR GPU'),
    (gen_random_uuid(), 'ocr_config', 'easyocr_enabled', 'true', NULL, 'EasyOCR enabled'),
    (gen_random_uuid(), 'ocr_config', 'easyocr_variant_label', 'autocontrast', NULL, 'EasyOCR variant label'),
    (gen_random_uuid(), 'ocr_config', 'line_cleanup_patterns', NULL, '["(?<=\\\\d)(?=[^\\\\W\\\\d_])","(?<=[^\\\\W\\\\d_])(?=\\\\d)"]'::jsonb, 'OCR line cleanup patterns'),
    (gen_random_uuid(), 'ocr_config', 'invoice_doc_number_context_tokens', NULL, '["factura","invoice","boleta","nota de venta","comprobante","documento","numero","nro"]'::jsonb, 'Invoice document number context tokens'),
    (gen_random_uuid(), 'ocr_config', 'invoice_doc_number_keyword_patterns', NULL, '["\\\\b(?:factura|invoice|boleta|nota de venta|comprobante|documento|numero|nro\\\\.?|no\\\\.?)\\\\b[^\\\\w]{0,20}((?:\\\\d{3}\\\\s*[-/ ]\\\\s*){2}\\\\d{3,15}|[A-Z]{1,8}[-/]?\\\\d{3,}[-/]?\\\\d*)","\\\\b(\\\\d{3}\\\\s*[-/ ]\\\\s*\\\\d{3}\\\\s*[-/ ]\\\\s*\\\\d{6,})\\\\b"]'::jsonb, 'Invoice document number keyword patterns'),
    (gen_random_uuid(), 'ocr_config', 'invoice_doc_number_fallback_patterns', NULL, '["\\\\b(\\\\d{3}[-/]\\\\d{3}[-/]\\\\d{6,})\\\\b","\\\\b(\\\\d{3}\\\\s*[-/ ]?\\\\s*\\\\d{3}\\\\s*[-/ ]?\\\\s*\\\\d{6,})\\\\b","\\\\b([A-Z]{1,8}[-/]\\\\d{3,}[-/]\\\\d{3,})\\\\b"]'::jsonb, 'Invoice document number fallback patterns'),
    (gen_random_uuid(), 'ocr_config', 'invoice_vendor_stop_tokens', NULL, '["datos del cliente","razon social","razon social / nombres y apellidos","nombres y apellidos","cliente","vendedor","ruc","c.i","direccion","telefono","email","correo","forma de pago","fecha de emision","fecha vencimiento","subtotal","total","iva","descuentos","ambiente","emision","autorizacion","producto"]'::jsonb, 'Invoice vendor stop tokens'),
    (gen_random_uuid(), 'ocr_config', 'invoice_vendor_suffix_patterns', NULL, '["\\\\b(?:s\\\\.?\\\\s*a\\\\.?\\\\s*|s\\\\.?\\\\s*a\\\\.?\\\\s*s\\\\.?|ltda\\\\.?|cia\\\\.?|compania|company|corp\\\\.?|inc\\\\.?|s\\\\.?\\\\s*r\\\\.?\\\\s*l\\\\.?|sas)\\\\b"]'::jsonb, 'Invoice vendor suffix patterns'),
    (gen_random_uuid(), 'ocr_config', 'invoice_line_skip_markers', NULL, '["subtotal","subtotal sin impuestos","sub total","iva","descuento","total","fecha","ruc","cliente","vendedor","direccion","telefono","email","forma de pago","entregar","ambiente","emision"]'::jsonb, 'Invoice line skip markers'),
    (gen_random_uuid(), 'ocr_config', 'excel_max_header_scan_rows', '25', NULL, 'Excel max header scan rows'),
    (gen_random_uuid(), 'ocr_config', 'excel_max_preview_rows_per_sheet', '120', NULL, 'Excel max preview rows per sheet'),
    (gen_random_uuid(), 'ocr_config', 'excel_scan_rows_multiplier', '4', NULL, 'Excel scan rows multiplier'),
    (gen_random_uuid(), 'ocr_config', 'excel_max_text_chars', '4000', NULL, 'Excel max text chars'),
    (gen_random_uuid(), 'ocr_config', 'vision_jpeg_quality', '75', NULL, 'Vision JPEG quality'),
    (gen_random_uuid(), 'ocr_config', 'image_source_formats', NULL, '["JPG","JPEG","PNG","IMG","HEIC","WEBP"]'::jsonb, 'Image source formats')
ON CONFLICT (module, key) DO NOTHING;

COMMIT;
