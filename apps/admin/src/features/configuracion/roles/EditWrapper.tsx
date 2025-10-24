import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { toast } from 'react-toastify'
import RoleForm from './RoleForm'
import type { RoleData, Role } from './types/roles'

interface EditWrapperProps {
  roles: Role[]
  onSubmit: (data: RoleData) => void
}

const EditWrapper: React.FC<EditWrapperProps> = ({ roles, onSubmit }) => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const roleId = Number(id)
  const role = roles.find(r => r.id === roleId)

  if (!role) {
    return <div className="p-6 text-center text-red-600">Rol no encontrado</div>
  }

  const roleAsRoleData: RoleData = {
    id: role.id,
    nombre: role.nombre,
    descripcion: role.descripcion,
    permisos: Object.entries(role.permisos)
      .filter(([, val]) => val)
      .map(([key]) => key),
  }

  const handleEditSubmit = (updatedRole: RoleData) => {
    onSubmit(updatedRole)
    toast.success('Rol actualizado correctamente', {
      position: 'top-right',
      autoClose: 1200,
      theme: 'colored',
    })
    setTimeout(() => navigate('/admin/configuracion/roles'), 1300)
  }

  return (
    <RoleForm
      mode="edit"
      initialData={roleAsRoleData}
      onSubmit={handleEditSubmit}
    />
  )
}

export default EditWrapper
