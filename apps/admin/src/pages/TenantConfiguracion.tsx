import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Tabs,
  Tab,
  Typography,
  TextField,
  Switch,
  FormControlLabel,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Divider,
  Alert,
  CircularProgress,
  IconButton,
  Breadcrumbs,
  Link,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import Grid from '@mui/material/Grid';
import {
  Save as SaveIcon,
  RestartAlt as RestartIcon,
  FileDownload as ExportIcon,
  Upload as UploadIcon,
  ArrowBack as BackIcon,
  Code as CodeIcon,
} from '@mui/icons-material';
import {
  getTenantSettings,
  updateTenantSettings,
  updateModuleSettings,
  uploadCertificate,
  exportSettings,
  restoreDefaults,
  TenantSettings,
} from '../services/tenant-settings';
import { listTimezones } from '../services/configuracion/timezones'
import { listLocales } from '../services/configuracion/locales'
import { listMonedas, type Moneda } from '../services/configuracion/monedas'
import { listPaises, type Pais } from '../services/configuracion/paises'
import { listSectores, type Sector } from '../services/configuracion/sectores';
import { getEmpresa, updateEmpresa } from '../services/empresa';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`config-tabpanel-${index}`}
      aria-labelledby={`config-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export default function TenantConfiguracion() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [tabValue, setTabValue] = useState(0);
  const [settings, setSettings] = useState<TenantSettings>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showJsonDialog, setShowJsonDialog] = useState(false);
  const [showRestoreDialog, setShowRestoreDialog] = useState(false);

  // Sector y Plantilla
  const [sectores, setSectores] = useState<Sector[]>([]);
  const [empresaData, setEmpresaData] = useState<any>(null);
  const [selectedSector, setSelectedSector] = useState<number | null>(null);
  const [selectedPlantilla, setSelectedPlantilla] = useState<string>('');

  // Certificate upload states
  const [sriCertFile, setSriCertFile] = useState<File | null>(null);
  const [sriCertPassword, setSriCertPassword] = useState('');
  const [siiCertFile, setSiiCertFile] = useState<File | null>(null);
  const [siiCertPassword, setSiiCertPassword] = useState('');
  const [uploadingCert, setUploadingCert] = useState(false);
  const [timezones, setTimezones] = useState<{ name: string; display_name: string }[]>([])
  const [locales, setLocales] = useState<{ code: string; name: string }[]>([])
  // Catálogos dinámicos
  const [monedas, setMonedas] = useState<Moneda[]>([])
  const [paises, setPaises] = useState<Pais[]>([])

  useEffect(() => {
    loadSettings();
    loadSectores();
    loadEmpresaData();
    // Cargar catálogos desde API (evitar hardcode)
    listMonedas()
      .then((rows) => setMonedas(rows.filter((r) => r.activo !== false)))
      .catch(() => setMonedas([]))
    listPaises().then((rows)=> setPaises(rows.filter(r=> r.active !== false))).catch(()=> setPaises([]))
    listTimezones().then((rows)=> setTimezones(rows.filter((r:any)=> r.active !== false))).catch(()=> setTimezones([]))
    listLocales().then((rows)=> setLocales(rows.filter((r:any)=> r.active !== false))).catch(()=> setLocales([]))
  }, [id]);

  const loadSettings = async () => {
    if (!id) return;

    try {
      setLoading(true);
      const data = await getTenantSettings(id);
      setSettings(data);

      // Cargar sector y plantilla desde settings
      setSelectedSector(data.sector_id || null);
      setSelectedPlantilla(data.sector_plantilla_name || '');
    } catch (err: any) {
      setError(err.message || 'Error cargando configuración');
    } finally {
      setLoading(false);
    }
  };

  const loadSectores = async () => {
    try {
      const data = await listSectores();
      setSectores(data);
    } catch (err) {
      console.error('Error loading sectores:', err);
    }
  };

  const loadEmpresaData = async () => {
    if (!id) return;
    try {
      const data = await getEmpresa(id);
      setEmpresaData(data);
    } catch (err) {
      console.error('Error loading empresa data:', err);
    }
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const updateField = (path: string, value: any) => {
    setSettings((prev) => {
      const keys = path.split('.');
      const newSettings = JSON.parse(JSON.stringify(prev));
      let current = newSettings;

      for (let i = 0; i < keys.length - 1; i++) {
        if (!current[keys[i]]) current[keys[i]] = {};
        current = current[keys[i]];
      }

      current[keys[keys.length - 1]] = value;
      return newSettings;
    });
  };

  const handleSave = async () => {
    if (!id) return;

    try {
      setSaving(true);

      // Guardar configuración avanzada + sector/plantilla en un solo call
      const settingsToSave = {
        ...settings,
        sector_id: selectedSector,
        sector_plantilla_nombre: selectedPlantilla || null,
      };

      await updateTenantSettings(id, settingsToSave);

      // Recargar configuración para confirmar el guardado
      await loadSettings();

      setSuccess('Configuración guardada correctamente');
    } catch (err: any) {
      setError(err.message || 'Error guardando configuración');
    } finally {
      setSaving(false);
    }
  };

  const handleExport = async () => {
    if (!id) return;

    try {
      const blob = await exportSettings(id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tenant-${id}-settings.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      setSuccess('Configuración exportada');
    } catch (err: any) {
      setError(err.message || 'Error exportando configuración');
    }
  };

  const handleRestoreDefaults = async () => {
    if (!id) return;

    try {
      await restoreDefaults(id);
      await loadSettings();
      setSuccess('Configuración restaurada a valores por defecto');
      setShowRestoreDialog(false);
    } catch (err: any) {
      setError(err.message || 'Error restaurando configuración');
    }
  };

  const handleUploadCertificate = async (type: 'sri' | 'sii') => {
    if (!id) return;

    const file = type === 'sri' ? sriCertFile : siiCertFile;
    const password = type === 'sri' ? sriCertPassword : siiCertPassword;

    if (!file || !password) {
      setError('Debe seleccionar un archivo y proporcionar la contraseña');
      return;
    }

    try {
      setUploadingCert(true);
      await uploadCertificate(id, type, file, password);
      setSuccess(`Certificado ${type.toUpperCase()} subido correctamente`);

      if (type === 'sri') {
        setSriCertFile(null);
        setSriCertPassword('');
      } else {
        setSiiCertFile(null);
        setSiiCertPassword('');
      }

      await loadSettings();
    } catch (err: any) {
      setError(err.message || 'Error subiendo certificado');
    } finally {
      setUploadingCert(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Breadcrumbs */}
      <Breadcrumbs sx={{ mb: 2 }}>
        <Link
          underline="hover"
          color="inherit"
          onClick={() => navigate('/admin')}
          sx={{ cursor: 'pointer' }}
        >
          Admin
        </Link>
        <Link
          underline="hover"
          color="inherit"
          onClick={() => navigate('/admin/empresas')}
          sx={{ cursor: 'pointer' }}
        >
          Empresas
        </Link>
        <Link
          underline="hover"
          color="inherit"
          onClick={() => navigate(`/admin/empresas/${id}`)}
          sx={{ cursor: 'pointer' }}
        >
          Detalle
        </Link>
        <Typography color="text.primary">Configuración Avanzada</Typography>
      </Breadcrumbs>

      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box display="flex" alignItems="center" gap={2}>
          <IconButton onClick={() => navigate(`/admin/empresas/${id}`)}>
            <BackIcon />
          </IconButton>
          <Typography variant="h4">⚙️ Configuración Avanzada</Typography>
        </Box>

        <Box display="flex" gap={1}>
          <Button
            variant="outlined"
            startIcon={<CodeIcon />}
            onClick={() => setShowJsonDialog(true)}
          >
            Ver JSON
          </Button>
          {empresaData?.slug && (
            <Button
              variant="outlined"
              onClick={() => window.open(`/admin/configuracion/campos?empresa=${encodeURIComponent(empresaData.slug)}&module=clientes`, '_blank')}
            >
              Campos (Clientes)
            </Button>
          )}
          <Button
            variant="outlined"
            startIcon={<ExportIcon />}
            onClick={handleExport}
          >
            Exportar
          </Button>
          <Button
            variant="outlined"
            color="warning"
            startIcon={<RestartIcon />}
            onClick={() => setShowRestoreDialog(true)}
          >
            Restaurar Defaults
          </Button>
          <Button
            variant="contained"
            startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
            onClick={handleSave}
            disabled={saving}
          >
            Guardar Todo
          </Button>
        </Box>
      </Box>

      {/* Main Content */}
      <Paper>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab label="General" />
          <Tab label="POS" />
          <Tab label="Inventario" />
          <Tab label="Facturación" />
          <Tab label="E-Factura" />
          <Tab label="Otros Módulos" />
        </Tabs>

        {/* Tab 0: General */}
        <TabPanel value={tabValue} index={0}>
          <Typography variant="h6" gutterBottom>
            Configuración General
          </Typography>
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 6 }}>
              <FormControl fullWidth>
                <InputLabel>Locale</InputLabel>
                <Select
                  value={settings.locale || ''}
                  onChange={(e) => updateField('locale', e.target.value)}
                  label="Locale"
                >
                  <MenuItem value=""><em>Detectar por defecto</em></MenuItem>
                  {locales.map((l) => (
                    <MenuItem key={l.code} value={l.code}>
                      {l.code} - {l.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <FormControl fullWidth>
                <InputLabel>Timezone</InputLabel>
                <Select
                  value={settings.timezone || ''}
                  onChange={(e) => updateField('timezone', e.target.value)}
                  label="Timezone"
                >
                  <MenuItem value=""><em>Detectar por defecto</em></MenuItem>
                  {timezones.map((tz) => (
                    <MenuItem key={tz.name} value={tz.name}>
                      {tz.display_name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <FormControl fullWidth>
                <InputLabel>Moneda</InputLabel>
                <Select
                  value={settings.currency || 'EUR'}
                  onChange={(e) => updateField('currency', e.target.value)}
                  label="Moneda"
                >
                  {monedas.map((m) => (
                    <MenuItem key={m.codigo} value={m.codigo}>
                      {m.codigo} - {m.nombre}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <FormControl fullWidth>
                <InputLabel>País</InputLabel>
                <Select
                  value={settings.country || 'ES'}
                  onChange={(e) => updateField('country', e.target.value)}
                  label="País"
                >
                  {paises.map((p) => (
                    <MenuItem key={p.code} value={p.code}>
                      {p.code} - {p.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid size={12}>
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 600 }}>
                🏢 Sector y Plantilla
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Selecciona el sector de negocio para aplicar configuraciones predefinidas
              </Typography>
            </Grid>

            <Grid size={{ xs: 12, md: 12 }}>
              <FormControl fullWidth>
                <InputLabel>Plantilla de Sector</InputLabel>
                <Select
                  value={selectedSector || ''}
                  onChange={(e) => {
                    const sectorId = e.target.value as number;
                    setSelectedSector(sectorId);
                    const sector = sectores.find(s => s.id === sectorId);
                    setSelectedPlantilla(sector?.sector_name || '');
                  }}
                  label="Plantilla de Sector"
                >
                  <MenuItem value="">
                    <em>Sin plantilla (configuración manual)</em>
                  </MenuItem>
                  {sectores.map((sector) => (
                    <MenuItem key={sector.id} value={sector.id}>
                      {sector.sector_name}
                    </MenuItem>
                  ))}
                </Select>
                {selectedSector && (
                  <Alert severity="info" sx={{ mt: 2 }}>
                    <strong>Plantilla seleccionada:</strong> {selectedPlantilla}
                    <br />
                    <Typography variant="caption">
                      Esta plantilla incluye configuraciones optimizadas para este tipo de negocio.
                    </Typography>
                  </Alert>
                )}
              </FormControl>
            </Grid>
          </Grid>
        </TabPanel>

        {/* Tab 1: POS */}
        <TabPanel value={tabValue} index={1}>
          <Typography variant="h6" gutterBottom>
            Configuración POS
          </Typography>
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 6 }}>
              <FormControl fullWidth>
                <InputLabel>Ancho de Ticket</InputLabel>
                <Select
                  value={settings.pos?.receipt_width_mm || 58}
                  onChange={(e) => updateField('pos.receipt_width_mm', e.target.value)}
                  label="Ancho de Ticket"
                >
                  <MenuItem value={58}>58mm</MenuItem>
                  <MenuItem value={80}>80mm</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                type="number"
                label="Tasa IVA Default (%)"
                value={(settings.pos?.default_tax_rate || 0) * 100}
                onChange={(e) => updateField('pos.default_tax_rate', parseFloat(e.target.value) / 100)}
                inputProps={{ min: 0, max: 100, step: 0.01 }}
              />
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                type="number"
                label="Días de Ventana de Devolución"
                value={settings.pos?.return_window_days || 15}
                onChange={(e) => updateField('pos.return_window_days', parseInt(e.target.value))}
                inputProps={{ min: 0 }}
              />
            </Grid>

            <Grid size={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.pos?.tax_price_includes || false}
                    onChange={(e) => updateField('pos.tax_price_includes', e.target.checked)}
                  />
                }
                label="Precios incluyen impuestos"
              />
            </Grid>

            <Grid size={12}>
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle1" gutterBottom>
                Store Credits (Vales)
              </Typography>
            </Grid>

            <Grid size={{ xs: 12, md: 4 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.pos?.store_credit?.enabled || false}
                    onChange={(e) => updateField('pos.store_credit.enabled', e.target.checked)}
                  />
                }
                label="Habilitar Store Credits"
              />
            </Grid>

            <Grid size={{ xs: 12, md: 4 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.pos?.store_credit?.single_use || true}
                    onChange={(e) => updateField('pos.store_credit.single_use', e.target.checked)}
                  />
                }
                label="Un Solo Uso"
              />
            </Grid>

            <Grid size={{ xs: 12, md: 4 }}>
              <TextField
                fullWidth
                type="number"
                label="Expiración (meses)"
                value={settings.pos?.store_credit?.expiry_months || 12}
                onChange={(e) => updateField('pos.store_credit.expiry_months', parseInt(e.target.value))}
                inputProps={{ min: 1 }}
              />
            </Grid>
          </Grid>
        </TabPanel>

        {/* Tab 2: Inventario */}
        <TabPanel value={tabValue} index={2}>
          <Typography variant="h6" gutterBottom>
            Configuración de Inventario
          </Typography>
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 6 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.inventory?.track_lots || false}
                    onChange={(e) => updateField('inventory.track_lots', e.target.checked)}
                  />
                }
                label="Rastrear Lotes"
              />
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.inventory?.track_expiry || false}
                    onChange={(e) => updateField('inventory.track_expiry', e.target.checked)}
                  />
                }
                label="Rastrear Caducidad"
              />
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.inventory?.allow_negative_stock || false}
                    onChange={(e) => updateField('inventory.allow_negative_stock', e.target.checked)}
                  />
                }
                label="Permitir Stock Negativo"
              />
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                type="number"
                label="Punto de Reorden Default"
                value={settings.inventory?.reorder_point_default || 10}
                onChange={(e) => updateField('inventory.reorder_point_default', parseInt(e.target.value))}
                inputProps={{ min: 0 }}
                helperText="Alerta cuando stock baje de este valor"
              />
            </Grid>
          </Grid>
        </TabPanel>

        {/* Tab 3: Facturación */}
        <TabPanel value={tabValue} index={3}>
          <Typography variant="h6" gutterBottom>
            Configuración de Facturación
          </Typography>
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 6 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.invoicing?.auto_numbering || true}
                    onChange={(e) => updateField('invoicing.auto_numbering', e.target.checked)}
                  />
                }
                label="Auto-Numeración"
              />
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.invoicing?.reset_yearly || true}
                    onChange={(e) => updateField('invoicing.reset_yearly', e.target.checked)}
                  />
                }
                label="Reiniciar Numeración Anualmente"
              />
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                label="Prefijo de Serie"
                value={settings.invoicing?.series_prefix || 'F'}
                onChange={(e) => updateField('invoicing.series_prefix', e.target.value)}
                helperText="Ej: F, FAC, INV"
              />
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                type="number"
                label="Número Inicial"
                value={settings.invoicing?.starting_number || 1}
                onChange={(e) => updateField('invoicing.starting_number', parseInt(e.target.value))}
                inputProps={{ min: 1 }}
              />
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.invoicing?.include_logo || true}
                    onChange={(e) => updateField('invoicing.include_logo', e.target.checked)}
                  />
                }
                label="Incluir Logo en Facturas"
              />
            </Grid>

            <Grid size={12}>
              <TextField
                fullWidth
                multiline
                rows={3}
                label="Texto de Pie de Página"
                value={settings.invoicing?.footer_text || ''}
                onChange={(e) => updateField('invoicing.footer_text', e.target.value)}
                helperText="Texto que aparecerá al pie de cada factura"
              />
            </Grid>
          </Grid>
        </TabPanel>

        {/* Tab 4: E-Factura */}
        <TabPanel value={tabValue} index={4}>
          <Typography variant="h6" gutterBottom>
            Configuración de E-Factura
          </Typography>

          {/* SRI Ecuador */}
          <Box sx={{ mb: 4 }}>
            <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold' }}>
              🇪🇨 SRI Ecuador
            </Typography>
            <Grid container spacing={3}>
              <Grid size={{ xs: 12, md: 6 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.einvoicing?.sri?.enabled || false}
                      onChange={(e) => updateField('einvoicing.sri.enabled', e.target.checked)}
                    />
                  }
                  label="Habilitar SRI"
                />
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <FormControl fullWidth>
                  <InputLabel>Entorno</InputLabel>
                  <Select
                    value={settings.einvoicing?.sri?.environment || 'staging'}
                    onChange={(e) => updateField('einvoicing.sri.environment', e.target.value)}
                    label="Entorno"
                    disabled={!settings.einvoicing?.sri?.enabled}
                  >
                    <MenuItem value="staging">Staging (Pruebas)</MenuItem>
                    <MenuItem value="production">Production</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid size={12}>
                <Divider />
                <Typography variant="body2" sx={{ mt: 2, mb: 1 }}>
                  Certificado Digital (.p12 / .pfx)
                </Typography>
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <Button
                  variant="outlined"
                  component="label"
                  fullWidth
                  startIcon={<UploadIcon />}
                  disabled={!settings.einvoicing?.sri?.enabled}
                >
                  {sriCertFile ? sriCertFile.name : 'Seleccionar Certificado'}
                  <input
                    type="file"
                    hidden
                    accept=".p12,.pfx"
                    onChange={(e) => setSriCertFile(e.target.files?.[0] || null)}
                  />
                </Button>
                {settings.einvoicing?.sri?.certificate_path && (
                  <Typography variant="caption" color="success.main" sx={{ mt: 1, display: 'block' }}>
                    ✓ Certificado configurado
                  </Typography>
                )}
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <TextField
                  fullWidth
                  type="password"
                  label="Contraseña del Certificado"
                  value={sriCertPassword}
                  onChange={(e) => setSriCertPassword(e.target.value)}
                  disabled={!settings.einvoicing?.sri?.enabled || !sriCertFile}
                />
              </Grid>

              <Grid size={12}>
                <Button
                  variant="contained"
                  onClick={() => handleUploadCertificate('sri')}
                  disabled={!sriCertFile || !sriCertPassword || uploadingCert}
                  startIcon={uploadingCert ? <CircularProgress size={20} /> : <UploadIcon />}
                >
                  Subir Certificado SRI
                </Button>
              </Grid>
            </Grid>
          </Box>

          <Divider sx={{ my: 3 }} />

          {/* SII España */}
          <Box>
            <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold' }}>
              🇪🇸 SII España
            </Typography>
            <Grid container spacing={3}>
              <Grid size={{ xs: 12, md: 6 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.einvoicing?.sii?.enabled || false}
                      onChange={(e) => updateField('einvoicing.sii.enabled', e.target.checked)}
                    />
                  }
                  label="Habilitar SII"
                />
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <TextField
                  fullWidth
                  label="Agencia"
                  value={settings.einvoicing?.sii?.agency || 'AEAT'}
                  onChange={(e) => updateField('einvoicing.sii.agency', e.target.value)}
                  disabled={!settings.einvoicing?.sii?.enabled}
                />
              </Grid>

              <Grid size={12}>
                <Divider />
                <Typography variant="body2" sx={{ mt: 2, mb: 1 }}>
                  Certificado Digital
                </Typography>
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <Button
                  variant="outlined"
                  component="label"
                  fullWidth
                  startIcon={<UploadIcon />}
                  disabled={!settings.einvoicing?.sii?.enabled}
                >
                  {siiCertFile ? siiCertFile.name : 'Seleccionar Certificado'}
                  <input
                    type="file"
                    hidden
                    accept=".p12,.pfx,.cer"
                    onChange={(e) => setSiiCertFile(e.target.files?.[0] || null)}
                  />
                </Button>
                {settings.einvoicing?.sii?.certificate_path && (
                  <Typography variant="caption" color="success.main" sx={{ mt: 1, display: 'block' }}>
                    ✓ Certificado configurado
                  </Typography>
                )}
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <TextField
                  fullWidth
                  type="password"
                  label="Contraseña del Certificado"
                  value={siiCertPassword}
                  onChange={(e) => setSiiCertPassword(e.target.value)}
                  disabled={!settings.einvoicing?.sii?.enabled || !siiCertFile}
                />
              </Grid>

              <Grid size={12}>
                <Button
                  variant="contained"
                  onClick={() => handleUploadCertificate('sii')}
                  disabled={!siiCertFile || !siiCertPassword || uploadingCert}
                  startIcon={uploadingCert ? <CircularProgress size={20} /> : <UploadIcon />}
                >
                  Subir Certificado SII
                </Button>
              </Grid>
            </Grid>
          </Box>

          <Divider sx={{ my: 3 }} />

          {/* Auto-send */}
          <Box>
            <FormControlLabel
              control={
                <Switch
                  checked={
                    settings.einvoicing?.sri?.auto_send ||
                    settings.einvoicing?.sii?.auto_send ||
                    false
                  }
                  onChange={(e) => {
                    updateField('einvoicing.sri.auto_send', e.target.checked);
                    updateField('einvoicing.sii.auto_send', e.target.checked);
                  }}
                />
              }
              label="Envío Automático de Facturas Electrónicas"
            />
            <Typography variant="caption" display="block" color="text.secondary">
              Las facturas se enviarán automáticamente al ser confirmadas
            </Typography>
          </Box>
        </TabPanel>

        {/* Tab 5: Otros Módulos */}
        <TabPanel value={tabValue} index={5}>
          <Typography variant="h6" gutterBottom>
            Configuración de Otros Módulos
          </Typography>
          <Alert severity="info" sx={{ mb: 2 }}>
            Configuración avanzada de módulos adicionales. Formato JSON personalizado.
          </Alert>

          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                multiline
                rows={4}
                label="Purchases Config (JSON)"
                value={JSON.stringify(settings.purchases || {}, null, 2)}
                onChange={(e) => {
                  try {
                    updateField('purchases', JSON.parse(e.target.value));
                  } catch (err) {
                    // Invalid JSON, ignore
                  }
                }}
              />
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                multiline
                rows={4}
                label="Expenses Config (JSON)"
                value={JSON.stringify(settings.expenses || {}, null, 2)}
                onChange={(e) => {
                  try {
                    updateField('expenses', JSON.parse(e.target.value));
                  } catch (err) {
                    // Invalid JSON, ignore
                  }
                }}
              />
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                multiline
                rows={4}
                label="Finance Config (JSON)"
                value={JSON.stringify(settings.finance || {}, null, 2)}
                onChange={(e) => {
                  try {
                    updateField('finance', JSON.parse(e.target.value));
                  } catch (err) {
                    // Invalid JSON, ignore
                  }
                }}
              />
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                multiline
                rows={4}
                label="HR Config (JSON)"
                value={JSON.stringify(settings.hr || {}, null, 2)}
                onChange={(e) => {
                  try {
                    updateField('hr', JSON.parse(e.target.value));
                  } catch (err) {
                    // Invalid JSON, ignore
                  }
                }}
              />
            </Grid>

            <Grid size={12}>
              <TextField
                fullWidth
                multiline
                rows={4}
                label="Sales Config (JSON)"
                value={JSON.stringify(settings.sales || {}, null, 2)}
                onChange={(e) => {
                  try {
                    updateField('sales', JSON.parse(e.target.value));
                  } catch (err) {
                    // Invalid JSON, ignore
                  }
                }}
              />
            </Grid>
          </Grid>
        </TabPanel>
      </Paper>

      {/* JSON Preview Dialog */}
      <Dialog
        open={showJsonDialog}
        onClose={() => setShowJsonDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Vista JSON Completa</DialogTitle>
        <DialogContent>
          <Box
            component="pre"
            sx={{
              bgcolor: 'grey.100',
              p: 2,
              borderRadius: 1,
              overflow: 'auto',
              fontSize: '0.875rem',
            }}
          >
            {JSON.stringify(settings, null, 2)}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowJsonDialog(false)}>Cerrar</Button>
        </DialogActions>
      </Dialog>

      {/* Restore Defaults Dialog */}
      <Dialog
        open={showRestoreDialog}
        onClose={() => setShowRestoreDialog(false)}
      >
        <DialogTitle>¿Restaurar Configuración por Defecto?</DialogTitle>
        <DialogContent>
          <Typography>
            Esta acción reemplazará toda la configuración actual con los valores por defecto.
            Esta operación no se puede deshacer.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowRestoreDialog(false)}>Cancelar</Button>
          <Button onClick={handleRestoreDefaults} color="warning" variant="contained">
            Restaurar
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbars */}
      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={() => setError(null)}
      >
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      </Snackbar>

      <Snackbar
        open={!!success}
        autoHideDuration={3000}
        onClose={() => setSuccess(null)}
      >
        <Alert severity="success" onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      </Snackbar>
    </Box>
  );
}
