import { useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { PlusCircle } from 'lucide-react'
import { Button } from '~/components/ui/button'
import { Input } from '~/components/ui/input'
import { Label } from '~/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '~/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '~/components/ui/select'
import { applyApiErrors } from '~/lib/form-errors'
import { createApplication } from '../api'
import type { ApplicationCountry } from '../types'

const schema = z.object({
  country: z.enum(['MX', 'CO']),
  full_name: z.string().min(2, 'Mínimo 2 caracteres'),
  document_number: z.string().min(1, 'Requerido'),
  amount_requested: z
    .string()
    .min(1, 'Requerido')
    .refine((v) => Number(v) > 0, 'Debe ser mayor a 0'),
  monthly_income: z
    .string()
    .min(1, 'Requerido')
    .refine((v) => Number(v) > 0, 'Debe ser mayor a 0'),
})

type FormValues = z.infer<typeof schema>

const DOCUMENT_PLACEHOLDER: Record<ApplicationCountry, string> = {
  MX: 'CURP — ej. PERJ800101HDFRZN09',
  CO: 'Cédula — ej. 1234567890',
}

export function CreateApplicationForm() {
  const [open, setOpen] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const {
    register,
    handleSubmit,
    control,
    setValue,
    reset,
    setError,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { country: 'MX' },
  })

  const country = (useWatch({ control, name: 'country' }) ?? 'MX') as ApplicationCountry

  const mutation = useMutation({
    mutationFn: createApplication,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications'] })
      setOpen(false)
      reset()
      setApiError(null)
    },
    onError: (err: unknown) => {
      const nonFieldError = applyApiErrors(err, setError, [
        'country',
        'full_name',
        'document_number',
        'amount_requested',
        'monthly_income',
      ] as const)
      setApiError(nonFieldError)
    },
  })

  function onSubmit(values: FormValues) {
    setApiError(null)
    mutation.mutate(values)
  }

  function handleOpenChange(value: boolean) {
    setOpen(value)
    if (!value) {
      reset()
      setApiError(null)
    }
  }

  return (
    <>
      <Button onClick={() => setOpen(true)}>
        <PlusCircle className="size-4 mr-2" />
        Nueva solicitud
      </Button>

      <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Nueva solicitud de crédito</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 pt-2">
          {apiError && (
            <p className="text-sm text-destructive rounded-md bg-destructive/10 px-3 py-2">
              {apiError}
            </p>
          )}

          {/* País */}
          <div className="space-y-1">
            <Label htmlFor="country">País</Label>
            <Select
              value={country}
              onValueChange={(v) => setValue('country', v as ApplicationCountry)}
            >
              <SelectTrigger id="country">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="MX">México</SelectItem>
                <SelectItem value="CO">Colombia</SelectItem>
              </SelectContent>
            </Select>
            {errors.country && (
              <p className="text-xs text-destructive">{errors.country.message}</p>
            )}
          </div>

          {/* Nombre */}
          <div className="space-y-1">
            <Label htmlFor="full_name">Nombre completo</Label>
            <Input id="full_name" {...register('full_name')} />
            {errors.full_name && (
              <p className="text-xs text-destructive">{errors.full_name.message}</p>
            )}
          </div>

          {/* Documento */}
          <div className="space-y-1">
            <Label htmlFor="document_number">Número de documento</Label>
            <Input
              id="document_number"
              placeholder={DOCUMENT_PLACEHOLDER[country]}
              {...register('document_number')}
            />
            {errors.document_number && (
              <p className="text-xs text-destructive">{errors.document_number.message}</p>
            )}
          </div>

          {/* Monto */}
          <div className="space-y-1">
            <Label htmlFor="amount_requested">Monto solicitado</Label>
            <Input
              id="amount_requested"
              type="number"
              min="0.01"
              step="0.01"
              placeholder="50000.00"
              {...register('amount_requested')}
            />
            {errors.amount_requested && (
              <p className="text-xs text-destructive">{errors.amount_requested.message}</p>
            )}
          </div>

          {/* Ingreso */}
          <div className="space-y-1">
            <Label htmlFor="monthly_income">Ingreso mensual</Label>
            <Input
              id="monthly_income"
              type="number"
              min="0.01"
              step="0.01"
              placeholder="15000.00"
              {...register('monthly_income')}
            />
            {errors.monthly_income && (
              <p className="text-xs text-destructive">{errors.monthly_income.message}</p>
            )}
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? 'Enviando...' : 'Crear solicitud'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
    </>
  )
}
