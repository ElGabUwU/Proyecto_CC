# Configuración de AWS S3 para Almacenamiento de Archivos

## ¿Por qué usar AWS S3?

Actualmente, los archivos de soporte (ingresos y egresos) se guardan localmente en el servidor. Esto significa que:
- ❌ Si cambias de dispositivo, no tendrás acceso a los archivos
- ❌ Si despliegas en producción, cada instancia tendrá sus propios archivos
- ❌ No hay respaldo automático de los documentos

**Solución:** Configurar AWS S3 para que todos los dispositivos accedan a los mismos archivos en la nube.

## Pasos para configurar AWS S3

### 1. Crear un Bucket en AWS S3

1. Inicia sesión en tu consola de AWS: https://console.aws.amazon.com/
2. Ve al servicio **S3**
3. Haz clic en **"Create bucket"**
4. Elige un nombre único (ej: `mi-consejo-comunal-soportes`)
5. Selecciona una región (ej: `us-east-1`)
6. Desmarca "Block all public access" si quieres que los archivos sean públicos (opcional)
7. Haz clic en **"Create bucket"**

### 2. Crear un Usuario IAM con Permisos

1. Ve al servicio **IAM** en AWS
2. Haz clic en **"Users"** → **"Add user"**
3. Nombre de usuario: `django-s3-user`
4. Marca **"Access key - Programmatic access"**
5. En permisos, selecciona **"Attach existing policies directly"**
6. Busca y marca **"AmazonS3FullAccess"** (o crea una política más restrictiva)
7. Haz clic en **"Next"** → **"Create user"**
8. **IMPORTANTE:** Descarga o copia las credenciales (Access Key ID y Secret Access Key)

### 3. Configurar el Bucket Policy (Opcional - Para archivos públicos)

Si quieres que los archivos sean accesibles públicamente:

1. Ve a tu bucket en S3
2. Pestaña **"Permissions"** → **"Bucket policy"**
3. Agrega esta política (reemplaza `TU_BUCKET_NAME`):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::TU_BUCKET_NAME/*"
        }
    ]
}
```

### 4. Configurar las Variables de Entorno

Edita tu archivo `.env` y agrega:

```env
AWS_ACCESS_KEY_ID=tu_access_key_id_aqui
AWS_SECRET_ACCESS_KEY=tu_secret_access_key_aqui
AWS_STORAGE_BUCKET_NAME=tu_bucket_name_aqui
AWS_S3_REGION_NAME=us-east-1
```

### 5. Reiniciar el Servidor

Después de configurar las variables, reinicia tu aplicación Django.

## ¿Cómo funciona ahora?

### Sin S3 (Configuración actual por defecto):
- Los archivos se guardan en: `/workspace/media/soportes/`
- Solo accesibles desde el dispositivo local
- URL: `/media/soportes/ingresos/archivo.pdf`

### Con S3 (Después de configurar):
- Los archivos se guardan en: AWS S3 Bucket
- Accesibles desde cualquier dispositivo
- URL: `https://tu-bucket.s3.amazonaws.com/soportes/ingresos/archivo.pdf`

## Migrar archivos existentes a S3

Si ya tienes archivos locales y quieres subirlos a S3:

```bash
# Instala AWS CLI
pip install awscli

# Configura tus credenciales
aws configure

# Sube todos los archivos locales a S3
aws s3 cp media/soportes/ s3://TU_BUCKET_NAME/soportes/ --recursive
```

## Verificación

Después de configurar S3:
1. Sube un archivo de soporte en Finanzas → Ingresos o Egresos
2. Verifica que la URL del archivo comience con `https://tu-bucket.s3.amazonaws.com/`
3. Accede a esa URL desde otro dispositivo para confirmar que funciona

## Notas Importantes

- ⚠️ **Nunca compartas tus credenciales de AWS**
- 💰 AWS S3 tiene costos (generalmente muy bajos para poco almacenamiento)
- 🔒 Puedes configurar políticas más restrictivas según necesites
- 📊 Monitorea el uso en la consola de AWS para controlar costos

## Soporte

Si tienes problemas:
1. Verifica que las credenciales sean correctas
2. Asegúrate de que el bucket exista en la región especificada
3. Revisa los permisos del usuario IAM
4. Consulta los logs de Django para errores específicos
