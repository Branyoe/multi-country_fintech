# Planeación — Country validators y CreditApplicationService

## Contexto general

Sistema de solicitudes de crédito multipaís (fintech). Django + Django REST Framework.
Los países implementados son MX y CO. El diseño debe ser extensible para agregar más países sin modificar código existente.

---

## Estructura de carpetas

```
apps/
    applications/
        countries/
            __init__.py
            base.py
            mx.py
            co.py
            registry.py
        models.py
        serializers.py
        services.py
        views.py
        urls.py
```

---

## 1. base.py

### Dataclass `BankData`

Representa la respuesta normalizada del proveedor bancario. Todos los campos opcionales excepto `provider_name` y `account_status`.

Campos:
- `provider_name: str`
- `account_status: str`
- `total_debt: float | None`
- `credit_score: int | None`
- `raw_response: dict`

### Clase abstracta `BaseCountryValidator`

Métodos abstractos que cada país debe implementar:

- `get_document_type() -> str`
  Retorna el nombre del tipo de documento del país (ej. "CURP", "CC", "DNI").

- `validate_document(document: str) -> tuple[bool, str]`
  Valida el formato del documento. Retorna `(es_valido, mensaje_error)`.
  Si es válido, mensaje_error es string vacío.

- `fetch_bank_data(document: str) -> BankData`
  Llama al proveedor bancario mock del país y retorna los datos normalizados en BankData.
  Esta llamada es síncrona en el MVP.
  Debe simular respuestas distintas por país con datos ficticios pero coherentes.

- `validate_financial_rules(amount: float, income: float, bank_data: BankData) -> tuple[bool, str]`
  Aplica las reglas financieras del país. Retorna `(es_valido, mensaje_error)`.

Métodos con implementación por defecto (pueden sobreescribirse):

- `get_initial_status() -> str`
  Retorna `"pending"` por defecto.

- `get_validation_rules() -> list[str]`
  Retorna lista de nombres de reglas que aplica este país. Usado para registrar en `country_validations`.

---

## 2. mx.py — MXCountryValidator

Hereda de `BaseCountryValidator`.

### `get_document_type`
Retorna `"CURP"`.

### `validate_document`
Valida formato CURP con regex:
- 18 caracteres
- Patrón: `^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d$`
- Convertir a uppercase antes de validar
- Error: `"CURP inválida — formato incorrecto"`

### `fetch_bank_data`
Simula respuesta del proveedor mexicano (estilo CNBV).
Retorna BankData con:
- `provider_name = "CNBV_MX"`
- `account_status = "active"`
- `total_debt` = valor fijo simulado
- `raw_response` con campos: `curp`, `score`, `deuda`

### `validate_financial_rules`
Regla: el monto solicitado no puede superar 5 veces el ingreso mensual.
- Si `amount > income * 5` → inválido
- Error: `"Monto supera 5 veces el ingreso mensual"`

---

## 3. co.py — COCountryValidator

Hereda de `BaseCountryValidator`.

### `get_document_type`
Retorna `"CC"`.

### `validate_document`
Valida formato Cédula de Ciudadanía colombiana:
- Solo dígitos
- Entre 6 y 10 caracteres
- Regex: `^\d{6,10}$`
- Error: `"Cédula inválida — debe tener entre 6 y 10 dígitos"`

### `fetch_bank_data`
Simula respuesta del proveedor colombiano (estilo Datacrédito).
Retorna BankData con:
- `provider_name = "DATACREDITO_CO"`
- `account_status = "active"`
- `total_debt` = valor fijo simulado
- `raw_response` con campos: `cc`, `deuda_total`, `estado`

### `validate_financial_rules`
Regla: la deuda total no puede superar el 40% del ingreso mensual.
- Si `bank_data.total_debt > income * 0.4` → inválido
- Error: `"Deuda total supera el 40% del ingreso mensual"`

---

## 4. registry.py

### Diccionario `COUNTRY_REGISTRY`

```python
COUNTRY_REGISTRY: dict[str, type[BaseCountryValidator]] = {
    "MX": MXCountryValidator,
    "CO": COCountryValidator,
}
```

### Función `get_validator(country_code: str) -> BaseCountryValidator`

- Busca en `COUNTRY_REGISTRY` con `country_code.upper()`
- Si no existe → lanza `ValueError(f"País no soportado: {country_code}")`
- Si existe → instancia y retorna el validator

---

## 5. services.py — CreditApplicationService

### Método `create(data: dict, user) -> CreditApplication`

Orquesta el flujo síncrono de creación. Pasos en orden:

1. Llamar `get_validator(data["country"])` → obtener validator
2. Llamar `validator.validate_document(data["document_number"])`
   - Si inválido → lanzar `ValidationError` con el mensaje
3. Llamar `validator.fetch_bank_data(data["document_number"])` → obtener `BankData`
   - Si falla → lanzar excepción con mensaje de error del proveedor
4. Llamar `validator.validate_financial_rules(data["amount_requested"], data["monthly_income"], bank_data)`
   - Si inválido → lanzar `ValidationError` con el mensaje
5. Crear instancia de `CreditApplication` con:
   - Todos los campos de `data`
   - `document_type = validator.get_document_type()`
   - `status = validator.get_initial_status()`
   - `user = user`
6. Crear instancia de `BankProviderData` asociada a la application con los datos de `BankData`
7. Crear filas en `CountryValidation` por cada regla evaluada (passed=True o False con detalle)
8. Disparar Celery task: `process_application.delay(str(application.id))`
9. Retornar la `application`

### Método `update_status(application_id: str, new_status: str, changed_by: str) -> CreditApplication`

1. Obtener `CreditApplication` por id → si no existe lanzar `NotFound`
2. Guardar `from_status = application.status`
3. Actualizar `application.status = new_status`
4. Guardar `application.save()`
5. Crear fila en `ApplicationStatusHistory` con `from_status`, `to_status`, `changed_by`
6. Retornar `application`

---

## Modelos involucrados (referencia)

- `CreditApplication`: tabla central
- `BankProviderData`: one-to-one con CreditApplication
- `CountryValidation`: one-to-many con CreditApplication, una fila por regla evaluada
- `ApplicationStatusHistory`: one-to-many con CreditApplication, una fila por transición

---

## Consideraciones adicionales

- Todos los métodos de validación deben ser puros (sin side effects), solo retornan resultado
- `fetch_bank_data` es el único método con side effect (llamada externa simulada)
- El service es el único responsable de persistir en DB y disparar tasks
- Los validators no conocen ni importan nada de Django (sin models, sin ORM)
- Agregar un nuevo país = crear archivo `xx.py` + registrar en `COUNTRY_REGISTRY`
- Los errores de validación deben ser capturados en la view y retornados como 422
- Los errores de proveedor bancario deben retornarse como 502