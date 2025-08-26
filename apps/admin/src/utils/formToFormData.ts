// src/utils/formToFormData.ts
import type { FormularioEmpresa } from "../typesall/empresa";

export const buildEmpresaFormData = (datos: FormularioEmpresa): FormData => {
  const form = new FormData();

  form.append("nombre", datos.nombre_empresa);
  if (datos.tipo_empresa) form.append("tipo_empresa_id", datos.tipo_empresa);
  if (datos.tipo_negocio) form.append("tipo_negocio_id", datos.tipo_negocio);
  if (datos.ruc) form.append("ruc", datos.ruc);
  if (datos.telefono) form.append("telefono", datos.telefono);
  if (datos.direccion) form.append("direccion", datos.direccion);
  if (datos.pais) form.append("pais", datos.pais);
  if (datos.provincia) form.append("provincia", datos.provincia);
  if (datos.ciudad) form.append("ciudad", datos.ciudad);
  if (datos.cp) form.append("cp", datos.cp);
  if (datos.sitio_web) form.append("sitio_web", datos.sitio_web);
  form.append("color_primario", datos.color_primario);
  form.append("plantilla_inicio", datos.plantilla_inicio || "cliente");
  form.append("config_json", datos.config_json || "{}");
  if (datos.logo) form.append("logo", datos.logo);

  form.append("nombre_encargado", datos.nombre_encargado);
  form.append("apellido_encargado", datos.apellido_encargado);
  form.append("email", datos.email);
  form.append("username", datos.username);
  form.append("password", datos.password);

  datos.modulos.forEach((id) => {
    form.append("modulos", id.toString());
  });

  return form;
};
