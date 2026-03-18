import React, { useState, useEffect } from 'react';

import {
    Save as SaveIcon,
    RestartAlt as RestartIcon,
    FileDownload as ExportIcon,
    ArrowBack as BackIcon,
    Code as CodeIcon,
} from '@mui/icons-material';
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
import { useParams, useNavigate } from 'react-router-dom';

import {
    getCompanySettings,
    updateCompanySettings,
    exportSettings,
    restoreDefaults,
    CompanySettings,
    getCompanyLimits,
    updateCompanyLimits,
    CompanyLimits,
    getCompanyBillingPlans,
    getCompanySubscription,
    subscribeCompany,
    changeCompanyPlan,
    cancelCompanySubscription,
    openCompanyBillingPortal,
    getCompanyFeatureFlags,
    updateCompanyFeatureFlags,
    type CompanyPlan,
    type CompanySubscription,
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
    const [billingPlans, setBillingPlans] = useState<CompanyPlan[]>([]);
    const [subscription, setSubscription] = useState<CompanySubscription | null>(null);
    const [billingLoading, setBillingLoading] = useState(false);
    const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('monthly');
    const [featureFlagsLoading, setFeatureFlagsLoading] = useState(false);
    const [featureFlags, setFeatureFlags] = useState<Record<string, boolean>>({});
    const [featureFlagSources, setFeatureFlagSources] = useState<Record<string, string>>({});
    const [featureFlagOverrides, setFeatureFlagOverrides] = useState<Record<string, boolean | null>>({});

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
            setBillingLoading(true);
            setFeatureFlagsLoading(true);
            const [plansData, subscriptionData, featureFlagsData] = await Promise.all([
                getCompanyBillingPlans(id).catch(() => []),
                getCompanySubscription(id).catch(() => null),
                getCompanyFeatureFlags(id).catch(() => null),
            ]);
            setBillingPlans(plansData);
            setSubscription(subscriptionData);
            setBillingCycle(subscriptionData?.billing_cycle === 'yearly' ? 'yearly' : 'monthly');
            setFeatureFlags(featureFlagsData?.flags || {});
            setFeatureFlagSources(featureFlagsData?.source || {});
            setFeatureFlagOverrides(featureFlagsData?.tenant_overrides || {});
        } catch (err: any) {
            setError(err.message || 'Error cargando configuración');
        } finally {
            setLoading(false);
            setLimitsLoading(false);
            setBillingLoading(false);
            setFeatureFlagsLoading(false);
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

    const refreshBilling = async () => {
        if (!id) return;
        try {
            setBillingLoading(true);
            const [plansData, subscriptionData] = await Promise.all([
                getCompanyBillingPlans(id).catch(() => []),
                getCompanySubscription(id).catch(() => null),
            ]);
            setBillingPlans(plansData);
            setSubscription(subscriptionData);
            setBillingCycle(subscriptionData?.billing_cycle === 'yearly' ? 'yearly' : 'monthly');
        } catch (err: any) {
            setError(err.message || 'Error cargando suscripciÃ³n');
        } finally {
            setBillingLoading(false);
        }
    };

    const handleSubscribeCompany = async (planId: string) => {
        if (!id) return;
        try {
            setBillingLoading(true);
            const result = await subscribeCompany(id, {
                plan_id: planId,
                billing_cycle: billingCycle,
                return_url: window.location.href,
            });
            if (result?.checkout_url) {
                window.location.href = result.checkout_url;
                return;
            }
            await refreshBilling();
            setSuccess('SuscripciÃ³n creada correctamente');
        } catch (err: any) {
            setError(err?.response?.data?.detail || err?.message || 'Error creando suscripciÃ³n');
        } finally {
            setBillingLoading(false);
        }
    };

    const handleChangeCompanyPlan = async (planId: string) => {
        if (!id) return;
        try {
            setBillingLoading(true);
            await changeCompanyPlan(id, { new_plan_id: planId, billing_cycle: billingCycle });
            await refreshBilling();
            setSuccess('Plan actualizado correctamente');
        } catch (err: any) {
            setError(err?.response?.data?.detail || err?.message || 'Error actualizando el plan');
        } finally {
            setBillingLoading(false);
        }
    };

    const handleCancelCompanySubscription = async () => {
        if (!id) return;
        if (!window.confirm('¿Cancelar la suscripción de esta empresa?')) return;
        try {
            setBillingLoading(true);
            await cancelCompanySubscription(id);
            await refreshBilling();
            setSuccess('SuscripciÃ³n cancelada correctamente');
        } catch (err: any) {
            setError(err?.response?.data?.detail || err?.message || 'Error cancelando suscripciÃ³n');
        } finally {
            setBillingLoading(false);
        }
    };

    const handleOpenBillingPortal = async () => {
        if (!id) return;
        try {
            setBillingLoading(true);
            const result = await openCompanyBillingPortal(id, { return_url: window.location.href });
            if (result?.portal_url) {
                window.location.href = result.portal_url;
                return;
            }
            setError('No se pudo abrir el portal de facturaciÃ³n');
        } catch (err: any) {
            setError(err?.response?.data?.detail || err?.message || 'Error abriendo el portal de facturaciÃ³n');
        } finally {
            setBillingLoading(false);
        }
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
            await updateCompanyFeatureFlags(id, {
                overrides: featureFlagOverrides,
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
                    <Tab label="Suscripción" />
                    <Tab label="Feature Flags" />
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

                <TabPanel value={tabValue} index={2}>
                    <Typography variant="h6" gutterBottom>
                        SuscripciÃ³n de la empresa
                    </Typography>
                    <Alert severity="info" sx={{ mb: 2 }}>
                        Gestiona el plan contratado de esta empresa desde admin.
                    </Alert>
                    {billingLoading ? (
                        <CircularProgress size={20} />
                    ) : (
                        <Box>
                            <Box sx={{ mb: 3, maxWidth: 260 }}>
                                <FormControl fullWidth>
                                    <InputLabel>Ciclo de facturaciÃ³n</InputLabel>
                                    <Select
                                        value={billingCycle}
                                        label="Ciclo de facturaciÃ³n"
                                        onChange={(e) => setBillingCycle(e.target.value as 'monthly' | 'yearly')}
                                    >
                                        <MenuItem value="monthly">Mensual</MenuItem>
                                        <MenuItem value="yearly">Anual</MenuItem>
                                    </Select>
                                </FormControl>
                            </Box>
                            {subscription ? (
                                <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
                                    <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                                        Plan actual: {subscription.plan?.display_name || subscription.plan?.name || 'Sin plan'}
                                    </Typography>
                                    <Box display="flex" gap={1} alignItems="center" flexWrap="wrap" mt={1}>
                                        <Chip
                                            label={subscription.status}
                                            color={
                                                subscription.status === 'active'
                                                    ? 'success'
                                                    : subscription.status === 'trialing'
                                                      ? 'info'
                                                      : subscription.status === 'past_due'
                                                        ? 'warning'
                                                        : 'default'
                                            }
                                        />
                                        <Chip
                                            label={subscription.billing_cycle === 'yearly' ? 'Anual' : 'Mensual'}
                                            variant="outlined"
                                        />
                                    </Box>
                                    {subscription.current_period_end && (
                                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                                            RenovaciÃ³n / fin de acceso: {new Date(subscription.current_period_end).toLocaleDateString()}
                                        </Typography>
                                    )}
                                    {subscription.trial_ends_at && (
                                        <Typography variant="body2" color="text.secondary">
                                            Trial hasta: {new Date(subscription.trial_ends_at).toLocaleDateString()}
                                        </Typography>
                                    )}
                                    <Box mt={2}>
                                        <Box display="flex" gap={1} flexWrap="wrap">
                                            <Button variant="outlined" onClick={handleOpenBillingPortal}>
                                                Portal de facturaciÃ³n
                                            </Button>
                                            <Button color="warning" variant="outlined" onClick={handleCancelCompanySubscription}>
                                                Cancelar suscripciÃ³n
                                            </Button>
                                        </Box>
                                    </Box>
                                </Paper>
                            ) : (
                                <Alert severity="warning" sx={{ mb: 3 }}>
                                    Esta empresa no tiene una suscripciÃ³n activa.
                                </Alert>
                            )}

                            <Grid container spacing={2}>
                                {billingPlans.map((plan) => {
                                    const isCurrent = plan.id === subscription?.plan?.id;
                                    return (
                                        <Grid key={plan.id} size={{ xs: 12, md: 4 }}>
                                            <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
                                                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                                                    {plan.display_name || plan.name}
                                                </Typography>
                                                <Typography variant="h5" sx={{ mt: 1 }}>
                                                    ${billingCycle === 'yearly' ? (plan.price_yearly ?? plan.price_monthly) : plan.price_monthly}
                                                    <Typography component="span" variant="body2" color="text.secondary">
                                                        {billingCycle === 'yearly' ? '/aÃ±o' : '/mes'}
                                                    </Typography>
                                                </Typography>
                                                {plan.price_yearly ? (
                                                    <Typography variant="body2" color="text.secondary">
                                                        ${plan.price_yearly}/aÃ±o
                                                    </Typography>
                                                ) : null}
                                                <Typography variant="body2" sx={{ mt: 2 }}>
                                                    Usuarios: {plan.max_users}
                                                </Typography>
                                                <Typography variant="body2">
                                                    Sucursales: {plan.max_branches}
                                                </Typography>
                                                <Box display="flex" gap={0.5} flexWrap="wrap" mt={1.5}>
                                                    {(plan.included_modules || []).map((moduleName) => (
                                                        <Chip key={`${plan.id}-${moduleName}`} label={moduleName} size="small" variant="outlined" />
                                                    ))}
                                                </Box>
                                                <Box mt={2}>
                                                    {isCurrent ? (
                                                        <Button fullWidth variant="contained" disabled>
                                                            Plan actual
                                                        </Button>
                                                    ) : subscription ? (
                                                        <Button fullWidth variant="contained" onClick={() => handleChangeCompanyPlan(plan.id)}>
                                                            Cambiar a este plan
                                                        </Button>
                                                    ) : (
                                                        <Button fullWidth variant="contained" onClick={() => handleSubscribeCompany(plan.id)}>
                                                            Crear suscripciÃ³n
                                                        </Button>
                                                    )}
                                                </Box>
                                            </Paper>
                                        </Grid>
                                    );
                                })}
                            </Grid>
                        </Box>
                    )}
                </TabPanel>

                <TabPanel value={tabValue} index={3}>
                    <Typography variant="h6" gutterBottom>
                        Feature flags del tenant
                    </Typography>
                    <Alert severity="info" sx={{ mb: 2 }}>
                        Override manual por tenant. Default elimina el override y deja actuar a entorno, pais, plan o valores globales.
                    </Alert>
                    {featureFlagsLoading ? (
                        <CircularProgress size={20} />
                    ) : (
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell>Flag</TableCell>
                                    <TableCell>Efectivo</TableCell>
                                    <TableCell>Fuente</TableCell>
                                    <TableCell>Override tenant</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {Object.keys(featureFlags).sort().map((flagName) => (
                                    <TableRow key={flagName}>
                                        <TableCell sx={{ fontFamily: 'monospace' }}>{flagName}</TableCell>
                                        <TableCell>
                                            <Chip
                                                size="small"
                                                label={featureFlags[flagName] ? 'enabled' : 'disabled'}
                                                color={featureFlags[flagName] ? 'success' : 'default'}
                                                variant={featureFlags[flagName] ? 'filled' : 'outlined'}
                                            />
                                        </TableCell>
                                        <TableCell>
                                            <Chip
                                                size="small"
                                                label={featureFlagSources[flagName] || 'default'}
                                                variant="outlined"
                                            />
                                        </TableCell>
                                        <TableCell sx={{ minWidth: 200 }}>
                                            <FormControl fullWidth size="small">
                                                <Select
                                                    value={
                                                        featureFlagOverrides[flagName] === true
                                                            ? 'true'
                                                            : featureFlagOverrides[flagName] === false
                                                                ? 'false'
                                                                : 'default'
                                                    }
                                                    onChange={(e) => {
                                                        const value = e.target.value;
                                                        setFeatureFlagOverrides((prev) => ({
                                                            ...prev,
                                                            [flagName]:
                                                                value === 'default'
                                                                    ? null
                                                                    : value === 'true',
                                                        }));
                                                    }}
                                                >
                                                    <MenuItem value="default">Default</MenuItem>
                                                    <MenuItem value="true">Enabled</MenuItem>
                                                    <MenuItem value="false">Disabled</MenuItem>
                                                </Select>
                                            </FormControl>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
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
