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
    getTenantSettings,
    updateTenantSettings,
    exportSettings,
    restoreDefaults,
    TenantSettings,
} from '../services/tenant-settings';
import { listSectores, type Sector } from '../services/configuracion/sectores';
import { getEmpresa } from '../services/empresa';

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
    const [selectedSector, setSelectedSector] = useState<string | null>(null);
    const [selectedPlantilla, setSelectedPlantilla] = useState<string>('');
    const [selectedPlantillaCode, setSelectedPlantillaCode] = useState<string>('');

    // Certificate upload states
    // CatÃ¡logos dinÃ¡micos
    useEffect(() => {
        loadSectores();
        loadEmpresaData();
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
            const data = await getTenantSettings(id);
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

    const handleSave = async () => {
        if (!id) return;

        try {
            setSaving(true);

            // Guardar configuración avanzada + sector/plantilla en un solo call
        await updateTenantSettings(id, {
            sector_id: selectedSector,
            sector_template_name: selectedPlantillaCode || null,
            sector_plantilla_nombre: selectedPlantilla || null,
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
                    <Tab label="Plantilla" />
                </Tabs>

                {/* Tab 0: Plantilla */}
                <TabPanel value={tabValue} index={0}>
                    <Typography variant="h6" gutterBottom>
                        Plantilla y sector
                    </Typography>
                    <Alert severity="info" sx={{ mb: 2 }}>
                        La configuracion operativa se gestiona desde el tenant en /settings/avanzado.
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

                
                

                
                

                {/* Tab 3: Facturación */}
                

                
                

                {/* Tab 5: Otros MÃ³dulos */}
                

                
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
                <DialogTitle>Â¿Restaurar Configuración por Defecto?</DialogTitle>
                <DialogContent>
                    <Typography>
                        Esta acción reemplazarÃ¡ toda la configuración actual con los valores por defecto.
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
