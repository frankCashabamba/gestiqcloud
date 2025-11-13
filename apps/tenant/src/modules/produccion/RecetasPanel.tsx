/**
 * RecetasPanel - Panel principal de gestión de recetas
 */

import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Button, IconButton, Tabs, Tab,
  Card, CardContent, CardActions, Grid, Chip, Alert
} from '@mui/material';
import { Add, Edit, Delete, ContentCopy, Calculate } from '@mui/icons-material';
import { listRecipes, deleteRecipe, type Recipe } from '../../services/api/recetas';
import RecetaForm from './RecetaForm';
import RecetaDetail from './RecetaDetail';
import CalculadoraProduccion from './CalculadoraProduccion';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div hidden={value !== index} {...other}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export default function RecetasPanel() {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Tabs
  const [currentTab, setCurrentTab] = useState(0);

  // Modales
  const [formOpen, setFormOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [calcOpen, setCalcOpen] = useState(false);

  // Selección
  const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null);
  const [editingRecipe, setEditingRecipe] = useState<Recipe | null>(null);

  // Cargar recetas
  useEffect(() => {
    loadRecipes();
  }, [currentTab]);

  const loadRecipes = async () => {
    try {
      setLoading(true);
      const activo = currentTab === 0 ? true : currentTab === 1 ? false : undefined;
      const data = await listRecipes({ activo });
      setRecipes(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Error al cargar recetas');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingRecipe(null);
    setFormOpen(true);
  };

  const handleEdit = (recipe: Recipe) => {
    setEditingRecipe(recipe);
    setFormOpen(true);
  };

  const handleDelete = async (recipeId: string) => {
    if (!confirm('¿Eliminar esta receta?')) return;

    try {
      await deleteRecipe(recipeId);
      loadRecipes();
    } catch (err: any) {
      alert('Error al eliminar: ' + err.message);
    }
  };

  const handleViewDetail = (recipe: Recipe) => {
    setSelectedRecipe(recipe);
    setDetailOpen(true);
  };

  const handleCalculate = (recipe: Recipe) => {
    setSelectedRecipe(recipe);
    setCalcOpen(true);
  };

  const handleFormClose = () => {
    setFormOpen(false);
    setEditingRecipe(null);
    loadRecipes();
  };

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Recetas de Producción</Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={handleCreate}
        >
          Nueva Receta
        </Button>
      </Box>

      {/* Error */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Tabs */}
      <Tabs value={currentTab} onChange={(_, v) => setCurrentTab(v)} sx={{ mb: 2 }}>
        <Tab label="Activas" />
        <Tab label="Inactivas" />
        <Tab label="Todas" />
      </Tabs>

      {/* Lista de recetas */}
      <TabPanel value={currentTab} index={currentTab}>
        {loading ? (
          <Typography>Cargando...</Typography>
        ) : recipes.length === 0 ? (
          <Alert severity="info">No hay recetas</Alert>
        ) : (
          <Grid container spacing={2}>
            {recipes.map((recipe) => (
              <Grid item xs={12} sm={6} md={4} key={recipe.id}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      {recipe.name}
                    </Typography>

                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Producto: {recipe.producto_nombre || 'N/A'}
                    </Typography>

                    <Box mt={2}>
                      <Chip
                        label={`${recipe.rendimiento} uds`}
                        size="small"
                        color="primary"
                        sx={{ mr: 1 }}
                      />
                      <Chip
                        label={`$${recipe.costo_por_unidad.toFixed(4)}/ud`}
                        size="small"
                        color="secondary"
                      />
                    </Box>

                    <Box mt={2}>
                      <Typography variant="body2">
                        Costo Total: <strong>${recipe.costo_total.toFixed(2)}</strong>
                      </Typography>
                      {recipe.tiempo_preparacion && (
                        <Typography variant="body2">
                          Tiempo: {recipe.tiempo_preparacion} min
                        </Typography>
                      )}
                    </Box>
                  </CardContent>

                  <CardActions>
                    <Button size="small" onClick={() => handleViewDetail(recipe)}>
                      Ver
                    </Button>
                    <IconButton size="small" onClick={() => handleEdit(recipe)}>
                      <Edit fontSize="small" />
                    </IconButton>
                    <IconButton size="small" onClick={() => handleCalculate(recipe)}>
                      <Calculate fontSize="small" />
                    </IconButton>
                    <IconButton size="small" onClick={() => handleDelete(recipe.id)}>
                      <Delete fontSize="small" />
                    </IconButton>
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </TabPanel>

      {/* Modales */}
      {formOpen && (
        <RecetaForm
          open={formOpen}
          recipe={editingRecipe}
          onClose={handleFormClose}
        />
      )}

      {detailOpen && selectedRecipe && (
        <RecetaDetail
          open={detailOpen}
          recipeId={selectedRecipe.id}
          onClose={() => setDetailOpen(false)}
        />
      )}

      {calcOpen && selectedRecipe && (
        <CalculadoraProduccion
          open={calcOpen}
          recipe={selectedRecipe}
          onClose={() => setCalcOpen(false)}
        />
      )}
    </Box>
  );
}
