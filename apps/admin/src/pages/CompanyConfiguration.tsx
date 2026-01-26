import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Box,
    Paper,
    Tabs,
    Tab,
    Typography,
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
    Switch,
    FormControlLabel,
    TextField,
    Chip,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableRow,
} from '@mui/material';
import Grid from '@mui/material/Grid';
import {
    Save as SaveIcon,
    RestartAlt as RestartIcon,
    FileDownload as ExportIcon,
    ArrowBack as BackIcon,
    Code as CodeIcon,
} from '@mui/icons-material';
import {
    getCompanySettings,
    updateCompanySettings,
    exportSettings,
    restoreDefaults,
    CompanySettings,
    getCompanyLimits,
    updateCompanyLimits,
    CompanyLimits,
} from '../services/company-settings';
import { listSectores, type Sector } from '../services/configuracion/sectores';
import { getEmpresa } from '../services/empresa';
import {
    backfillPosReceiptDocuments,
    listPosBackfillCandidates,
    type POSBackfillResult,
    type POSBackfillCandidate,
} from '../services/posBackfill';

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

export default function CompanyConfiguration() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();

    const [tabValue, setTabValue] = useState(0);
    const [settings, setSettings] = useState<CompanySettings>({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    const [showJsonDialog, setShowJsonDialog] = useState(false);
    const [showRestoreDialog, setShowRestoreDialog] = useState(false);
    const [showPosBackfillDialog, setShowPosBackfillDialog] = useState(false);
    const [posReceiptId, setPosReceiptId] = useState('');
    const [posBackfillLoading, setPosBackfillLoading] = useState(false);
    const [posBackfillError, setPosBackfillError] = useState<string | null>(null);
    const [posBackfillResult, setPosBackfillResult] = useState<POSBackfillResult | null>(null);
    const [posCandidatesLoading, setPosCandidatesLoading] = useState(false);
    const [posCandidates, setPosCandidates] = useState<POSBackfillCandidate[]>([]);
    const [posCandidatesMissing, setPosCandidatesMissing] = useState<'any' | 'invoice' | 'sale'>('any');
    const [posCandidatesSince, setPosCandidatesSince] = useState<string>(() => {
        const d = new Date();
        d.setDate(d.getDate() - 7);
        return d.toISOString();
    });

    // Sector y Plantilla
    const [sectores, setSectores] = useState<Sector[]>([]);
    const [empresaData, setEmpresaData] = useState<any>(null);
    const [selectedSector, setSelectedSector] = useState<string | null>(null);
    const [selectedPlantilla, setSelectedPlantilla] = useState<string>('');
    const [selectedPlantillaCode, setSelectedPlantillaCode] = useState<string>('');
    const [limits, setLimits] = useState<CompanyLimits>({ user_limit: 10, allow_custom_roles: true });
    const [limitsLoading, setLimitsLoading] = useState(false);

    // Certificate upload states
    // CatÃ¡logos dinÃ¡micos
    useEffect(() => {
        loadSectors();
        loadCompanyData();
        // Cargar catÃ¡logos desde API (evitar hardcode)
    }, [id]);

    // Cargar settings DESPUÃ‰S de que sectores estÃ© listo
    useEffect(() => {
        if (sectores.length > 0) {
            loadSettings();
        }
    }, [id, sectores]);

    const loadSettings = async () => {
        if (!id) return;

        try {
            setLoading(true);
            const data = await getCompanySettings(id);
            setSettings(data);

            // âœ… CORRECCIÃ“N: Usar sector_template_name en lugar de sector_id
            // El backend guarda el NOMBRE del sector en sector_template_name (STRING)
            // Ejemplo: "panaderia", "taller", "retail"
            // NO usa sector_id (INT/NULL)

            if (data.sector_template_name && sectores.length > 0) {
                // Buscar el sector en la lista cargada usando el nombre/code
                const matchingSector = sectores.find(
                    (s) =>
                        s.code === data.sector_template_name ||
                        s.name === data.sector_template_name ||
                        s.id === data.sector_template_name
                );

                if (matchingSector) {
                    setSelectedSector(matchingSector.id);
                    setSelectedPlantilla(matchingSector.name);
                    setSelectedPlantillaCode(matchingSector.code || '');
                } else {
                    setSelectedSector(null);
                    setSelectedPlantilla('');
                    setSelectedPlantillaCode('');
                }
            } else {
                setSelectedSector(null);
                setSelectedPlantilla('');
                setSelectedPlantillaCode('');
            }
            setLimitsLoading(true);
            const limitsData = await getCompanyLimits(id);
            setLimits(limitsData || { user_limit: 10, allow_custom_roles: true });
        } catch (err: any) {
            setError(err.message || 'Error cargando configuración');
        } finally {
            setLoading(false);
            setLimitsLoading(false);
        }
    };

    const handlePosBackfill = async (receiptIdOverride?: string) => {
        if (!id) return;
        const receipt = String(receiptIdOverride ?? posReceiptId ?? '').trim();
        if (!receipt) {
            setPosBackfillError('Receipt ID requerido');
            setError('Receipt ID requerido');
            return;
        }

        try {
            setPosBackfillLoading(true);
            setPosBackfillError(null);
            setPosBackfillResult(null);
            setError(null);
            const result = await backfillPosReceiptDocuments(id, receipt);
            setPosBackfillResult(result);
            
            // Check if documents were created
            const docsCreated = Object.keys(result?.documents_created ?? {}).length > 0;
            if (docsCreated) {
                setSuccess(`✓ Backfill completado: ${Object.keys(result.documents_created ?? {}).join(', ')}`);
            } else {
                setSuccess('✓ Backfill ejecutado (documentos ya existían)');
            }
            
            // Reload candidates to update UI after successful backfill
            await new Promise(resolve => setTimeout(resolve, 500)); // Small delay for DB sync
            await loadPosCandidates();
            setPosReceiptId('');
        } catch (err: any) {
            const message =
                err?.response?.data?.detail ||
                err?.response?.data?.message ||
                err?.message ||
                'Error ejecutando backfill POS';
            const errMsg = String(message);
            setPosBackfillError(errMsg);
            setError(errMsg);
        } finally {
            setPosBackfillLoading(false);
        }
    };

    const loadPosCandidates = async (missingOverride?: 'any' | 'invoice' | 'sale') => {
        if (!id) return;
        try {
            setPosCandidatesLoading(true);
            setPosBackfillError(null);
            const missingValue = missingOverride ?? posCandidatesMissing;
            const res = await listPosBackfillCandidates(id, {
                missing: missingValue,
                since: posCandidatesSince,
                limit: 50,
                offset: 0,
            });
            setPosCandidates(res?.items ?? []);
        } catch (err: any) {
            const message =
                err?.response?.data?.detail ||
                err?.response?.data?.message ||
                err?.message ||
                'Error listando receipts incompletos';
            setPosBackfillError(String(message));
        } finally {
            setPosCandidatesLoading(false);
        }
    };

    const loadSectors = async () => {
        try {
            const data = await listSectores();
            setSectores(data);
        } catch (err) {
            console.error('Error loading sectores:', err);
        }
    };

    const loadCompanyData = async () => {
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

    const handleSave = async () => {
        if (!id) return;

        try {
            setSaving(true);

            // Guardar configuraci?n avanzada + sector/plantilla en un solo call
            await updateCompanySettings(id, {
                sector_id: selectedSector,
                sector_template_name: selectedPlantillaCode || null,
                sector_plantilla_nombre: selectedPlantilla || null,
            });
            await updateCompanyLimits(id, {
                user_limit: limits.user_limit,
                allow_custom_roles: limits.allow_custom_roles,
            });

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
                    onClick={() => navigate('/admin/companies')}
                    sx={{ cursor: 'pointer' }}
                >
                    Empresas
                </Link>
                <Link
                    underline="hover"
                    color="inherit"
                    onClick={() => navigate(`/admin/companies/${id}`)}
                    sx={{ cursor: 'pointer' }}
                >
                    Detalle
                </Link>
                <Typography color="text.primary">Configuración Avanzada</Typography>
            </Breadcrumbs>

            {/* Header */}
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                <Box display="flex" alignItems="center" gap={2}>
                    <IconButton onClick={() => navigate(`/admin/companies/${id}`)}>
                        <BackIcon />
                    </IconButton>
                    <Typography variant="h4">Configuración Avanzada</Typography>
                </Box>

                <Box display="flex" gap={1}>
                    <Button
                        variant="outlined"
                        startIcon={<CodeIcon />}
                        onClick={() => setShowJsonDialog(true)}
                    >
                        Ver JSON
                    </Button>
                    <Button
                        variant="outlined"
                        color="secondary"
                        onClick={() => {
                            setShowPosBackfillDialog(true);
                            setPosBackfillError(null);
                            setPosBackfillResult(null);
                            setPosReceiptId('');
                            loadPosCandidates();
                        }}
                    >
                        Rescate POS
                    </Button>
                    {empresaData?.slug && (
                        <Button
                            variant="outlined"
                            onClick={() => window.open(`/admin/config/fields?empresa=${encodeURIComponent(empresaData.slug)}&module=clientes`, '_blank')}
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
                        Save All
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
                    <Tab label="Plantilla" />
                    <Tab label="Limites" />
                </Tabs>

                {/* Tab 0: Plantilla */}
                <TabPanel value={tabValue} index={0}>
                    <Typography variant="h6" gutterBottom>
                        Plantilla y sector
                    </Typography>
                    <Alert severity="info" sx={{ mb: 2 }}>
                        La configuracion operativa se gestiona desde el tenant en /settings/operativo.
                    </Alert>
                    <Grid container spacing={3}>
                        <Grid size={12}>
                            <Divider sx={{ my: 2 }} />
                            <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 600 }}>
                                Sector y Plantilla
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
                                        const sectorId = (e.target.value as string) || null;
                                        setSelectedSector(sectorId);
                                        const sector = sectores.find(s => s.id === sectorId);
                                        setSelectedPlantilla(sector?.name || '');
                                        setSelectedPlantillaCode(sector?.code || '');
                                    }}
                                    label="Plantilla de Sector"
                                >
                                    <MenuItem value="">
                                        <em>Sin plantilla (configuración manual)</em>
                                    </MenuItem>
                                    {sectores.map((sector) => (
                                        <MenuItem key={sector.id} value={sector.id}>
                                            {sector.name}
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

                <TabPanel value={tabValue} index={1}>
                    <Typography variant="h6" gutterBottom>
                        Limites del plan
                    </Typography>
                    <Alert severity="info" sx={{ mb: 2 }}>
                        Estos valores controlan el maximo de usuarios permitidos por empresa.
                    </Alert>
                    {limitsLoading ? (
                        <CircularProgress size={20} />
                    ) : (
                        <Grid container spacing={3}>
                            <Grid size={{ xs: 12, md: 6 }}>
                                <FormControl fullWidth>
                                    <InputLabel>Usuarios maximos</InputLabel>
                                    <Select
                                        value={limits.user_limit ?? 10}
                                        onChange={(e) =>
                                            setLimits((prev) => ({
                                                ...prev,
                                                user_limit: Number(e.target.value),
                                            }))
                                        }
                                        label="Usuarios maximos"
                                    >
                                        {[1, 3, 5, 10, 20, 50, 100].map((opt) => (
                                            <MenuItem key={opt} value={opt}>
                                                {opt}
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                            </Grid>
                            <Grid size={{ xs: 12, md: 6 }}>
                                <FormControlLabel
                                    control={
                                        <Switch
                                            checked={!!limits.allow_custom_roles}
                                            onChange={(e) =>
                                                setLimits((prev) => ({
                                                    ...prev,
                                                    allow_custom_roles: e.target.checked,
                                                }))
                                            }
                                        />
                                    }
                                    label="Permitir roles personalizados"
                                />
                            </Grid>
                        </Grid>
                    )}
                </TabPanel>

                
                

                
                

                {/* Tab 3: Facturación */}
                

                
                

                {/* Tab 5: Otros MÃ³dulos */}
                

                
            </Paper>

            {/* POS Backfill Dialog */}
            <Dialog
                open={showPosBackfillDialog}
                onClose={() => (posBackfillLoading ? null : setShowPosBackfillDialog(false))}
                maxWidth="sm"
                fullWidth
            >
                <DialogTitle>Rescate POS (backfill documentos)</DialogTitle>
                <DialogContent>
                    <Alert severity="info" sx={{ mb: 2 }}>
                        Reintenta crear documentos faltantes (factura + orden de venta) para un receipt ya pagado.
                    </Alert>

                    <Box sx={{ mb: 2 }}>
                        <Box display="flex" gap={1} alignItems="center" flexWrap="wrap">
                            <Chip
                                label="Faltan: cualquiera"
                                color={posCandidatesMissing === 'any' ? 'primary' : 'default'}
                                onClick={() => {
                                    setPosCandidatesMissing('any');
                                    loadPosCandidates('any');
                                }}
                                variant={posCandidatesMissing === 'any' ? 'filled' : 'outlined'}
                            />
                            <Chip
                                label="Solo factura"
                                color={posCandidatesMissing === 'invoice' ? 'primary' : 'default'}
                                onClick={() => {
                                    setPosCandidatesMissing('invoice');
                                    loadPosCandidates('invoice');
                                }}
                                variant={posCandidatesMissing === 'invoice' ? 'filled' : 'outlined'}
                            />
                            <Chip
                                label="Solo venta"
                                color={posCandidatesMissing === 'sale' ? 'primary' : 'default'}
                                onClick={() => {
                                    setPosCandidatesMissing('sale');
                                    loadPosCandidates('sale');
                                }}
                                variant={posCandidatesMissing === 'sale' ? 'filled' : 'outlined'}
                            />
                            <Button
                                size="small"
                                variant="outlined"
                                onClick={() => loadPosCandidates()}
                                disabled={posCandidatesLoading || posBackfillLoading}
                            >
                                Refrescar
                            </Button>
                        </Box>
                        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                            Mostrando últimos 7 días (pagados). Puedes ejecutar por fila o pegar el UUID manualmente.
                        </Typography>
                    </Box>

                    {posCandidatesLoading ? (
                        <Box display="flex" justifyContent="center" sx={{ my: 2 }}>
                            <CircularProgress size={22} />
                        </Box>
                    ) : posCandidates.length > 0 ? (
                        <Table size="small" sx={{ mb: 2 }} key={`pos-table-${posCandidates.length}`}>
                            <TableHead>
                                <TableRow>
                                    <TableCell>Receipt</TableCell>
                                    <TableCell>Total</TableCell>
                                    <TableCell>Faltantes</TableCell>
                                    <TableCell align="right">Acción</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {posCandidates.map((c, idx) => (
                                    <TableRow key={`${c.receipt_id}-${idx}`}>
                                        <TableCell>
                                            <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                                {c.number || c.receipt_id}
                                            </Typography>
                                            <Typography variant="caption" color="text.secondary">
                                                {c.paid_at ? new Date(c.paid_at).toLocaleString() : ''}
                                            </Typography>
                                        </TableCell>
                                        <TableCell>
                                            {c.gross_total?.toFixed?.(2) ?? String(c.gross_total)} {c.currency || ''}
                                        </TableCell>
                                        <TableCell>
                                            <Box display="flex" gap={0.5} flexWrap="wrap">
                                                {c.missing_invoice && <Chip size="small" label="Factura" color="warning" />}
                                                {c.missing_sale && <Chip size="small" label="Venta" color="warning" />}
                                                {!c.missing_invoice && !c.missing_sale && <Chip size="small" label="✓ Completado" color="success" variant="outlined" />}
                                            </Box>
                                        </TableCell>
                                        <TableCell align="right">
                                            <Button
                                                size="small"
                                                variant="contained"
                                                onClick={async () => {
                                                    const receiptId = String(c.receipt_id);
                                                    setPosReceiptId(receiptId);
                                                    await handlePosBackfill(receiptId);
                                                    await loadPosCandidates();
                                                }}
                                                disabled={posBackfillLoading || (!c.missing_invoice && !c.missing_sale)}
                                                title={!c.missing_invoice && !c.missing_sale ? 'Documentos completados' : ''}
                                            >
                                                Ejecutar
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    ) : (
                        <Alert severity="success" sx={{ mb: 2 }}>
                            No hay receipts incompletos en el rango actual.
                        </Alert>
                    )}

                    <TextField
                        fullWidth
                        label="Receipt ID (UUID)"
                        value={posReceiptId}
                        onChange={(e) => setPosReceiptId(e.target.value)}
                        placeholder="b2d42b0b-9c17-4068-aa8d-7d09230a423b"
                        disabled={posBackfillLoading}
                    />
                    {posBackfillError && (
                        <Alert severity="error" sx={{ mt: 2 }}>
                            {posBackfillError}
                        </Alert>
                    )}
                    {posBackfillResult && (
                        <Box
                            component="pre"
                            sx={{
                                mt: 2,
                                bgcolor: 'grey.100',
                                p: 2,
                                borderRadius: 1,
                                overflow: 'auto',
                                fontSize: '0.875rem',
                            }}
                        >
                            {JSON.stringify(posBackfillResult, null, 2)}
                        </Box>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setShowPosBackfillDialog(false)} disabled={posBackfillLoading}>
                        Cerrar
                    </Button>
                </DialogActions>
            </Dialog>

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
                <DialogTitle>Restore default configuration?</DialogTitle>
                <DialogContent>
                    <Typography>
                        This action will replace all current configuration with default values.
                        This operation cannot be undone.
                    </Typography>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setShowRestoreDialog(false)}>Cancel</Button>
                    <Button onClick={handleRestoreDefaults} color="warning" variant="contained">
                        Restore
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
