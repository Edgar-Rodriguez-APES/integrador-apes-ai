#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para crear productos usando template CSV con el API de Kong RFID WMS
Basado en product_rfid_template_load.csv
Autor: Kong RFID WMS Team
Fecha: 2025-08-25
"""

import requests
import json
import sys
import csv
import os
import argparse
from typing import Dict, List, Optional
from urllib.parse import urljoin


class ProductCreatorFromCSV:
    """Clase para crear productos desde template CSV"""
    
    def __init__(self):
        self.session = requests.Session()
        self.api_url = None
        self.token = None
        self.endpoint = "inventory/skus/"
    
    def setup_session(self, api_url: str, token: str):
        """Configurar la sesión HTTP con URL base y token"""
        self.api_url = api_url.rstrip('/')
        self.token = token
        
        self.session.headers.update({
            'Authorization': f'Token {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Validar conectividad
        try:
            test_url = urljoin(f"{self.api_url}/", self.endpoint)
            response = self.session.get(test_url, params={'limit': 1})
            response.raise_for_status()
            print(f"✅ Conexión exitosa al API: {self.api_url}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Error de conexión al API: {e}")
            return False
    
    def validate_csv_file(self, csv_file_path: str) -> Dict:
        """Validar el archivo CSV y retornar información sobre las columnas"""
        if not os.path.exists(csv_file_path):
            raise ValueError(f"El archivo CSV no existe: {csv_file_path}")
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8-sig') as file:  # utf-8-sig para manejar BOM
                reader = csv.DictReader(file)
                fieldnames = reader.fieldnames
                
                if not fieldnames:
                    raise ValueError("El archivo CSV está vacío o no tiene headers")
                
                # Limpiar nombres de columnas (remover BOM y espacios)
                clean_fieldnames = []
                for col in fieldnames:
                    clean_col = col.strip()
                    # Remover BOM manualmente si aún existe
                    if clean_col.startswith('\ufeff'):
                        clean_col = clean_col[1:]
                    clean_fieldnames.append(clean_col)
                
                # Contar filas de datos
                rows = list(reader)
                total_rows = len(rows)
                
                # Limpiar las claves de cada fila también
                clean_rows = []
                for row in rows:
                    clean_row = {}
                    for orig_key, value in row.items():
                        clean_key = orig_key.strip()
                        if clean_key.startswith('\ufeff'):
                            clean_key = clean_key[1:]
                        clean_row[clean_key] = value
                    clean_rows.append(clean_row)
                
                # Separar columnas normales y custom
                standard_columns = []
                custom_columns = []
                
                for col in clean_fieldnames:
                    if col.startswith('custom:'):
                        custom_columns.append(col)
                    elif col.strip():  # Solo agregar columnas no vacías
                        standard_columns.append(col)
                
                return {
                    'total_rows': total_rows,
                    'fieldnames': clean_fieldnames,
                    'standard_columns': standard_columns,
                    'custom_columns': custom_columns,
                    'rows': clean_rows
                }
        except Exception as e:
            raise ValueError(f"Error al leer el archivo CSV: {e}")
    
    def get_user_input(self) -> Dict:
        """Obtener datos del usuario"""
        print("\n🏗️  CREADOR DE PRODUCTOS DESDE CSV")
        print("=" * 50)
        
        # Archivo CSV
        default_csv = "/home/andresciceri/projects/apes/scripts/python/product_rfid_template_load.csv"
        csv_file = input(f"📄 Archivo CSV (enter para usar {os.path.basename(default_csv)}): ").strip()
        if not csv_file:
            csv_file = default_csv
        
        # Validar archivo CSV
        try:
            csv_info = self.validate_csv_file(csv_file)
            print(f"✅ Archivo CSV válido: {csv_info['total_rows']} productos encontrados")
            print(f"   Columnas estándar: {', '.join(csv_info['standard_columns'])}")
            if csv_info['custom_columns']:
                custom_names = [col.replace('custom:', '') for col in csv_info['custom_columns']]
                print(f"   Propiedades custom: {', '.join(custom_names)}")
        except ValueError as e:
            raise ValueError(f"Error en archivo CSV: {e}")
        
        # URL del API
        api_url = input("🌐 URL del API (ej: https://api-kong-wms.com): ").strip()
        if not api_url:
            raise ValueError("La URL del API es requerida")
        
        # Token
        token = input("🔑 Token de autenticación: ").strip()
        if not token:
            raise ValueError("El token es requerido")
        
        # Configurar sesión
        if not self.setup_session(api_url, token):
            raise ValueError("No se pudo conectar al API")
        
        # Type ID
        try:
            type_id = int(input("📋 Type ID: ").strip())
            if type_id <= 0:
                raise ValueError("El Type ID debe ser mayor a 0")
        except ValueError as e:
            if "invalid literal" in str(e):
                raise ValueError("El Type ID debe ser un número válido")
            raise
        
        # Group ID
        try:
            group_id = int(input("📦 Group ID: ").strip())
            if group_id < 0:
                raise ValueError("El Group ID debe ser mayor o igual a 0")
        except ValueError as e:
            if "invalid literal" in str(e):
                raise ValueError("El Group ID debe ser un número válido")
            raise
        
        # Customer ID
        try:
            customer_id = int(input("👤 Customer ID: ").strip())
            if customer_id <= 0:
                raise ValueError("El Customer ID debe ser mayor a 0")
        except ValueError as e:
            if "invalid literal" in str(e):
                raise ValueError("El Customer ID debe ser un número válido")
            raise
        
        return {
            'csv_file': csv_file,
            'csv_info': csv_info,
            'type_id': type_id,
            'group_id': group_id,
            'customer_id': customer_id
        }
    
    def row_to_payload(self, row: Dict, config: Dict) -> Dict:
        """Convertir una fila del CSV a payload JSON"""
        # Campos estándar
        payload = {
            "type_id": config['type_id'],
            "group_id": config['group_id'],
            "customer_id": config['customer_id'],
            "is_active": True
        }
        
        # Agregar campos estándar del CSV
        for col in config['csv_info']['standard_columns']:
            if col in row and row[col] is not None:
                value = str(row[col]).strip()
                if value:  # Solo procesar si hay un valor no vacío
                    # Convertir ciertos campos a enteros si es necesario
                    if col == 'id':
                        try:
                            # Para 'id' mantener como string si es muy largo para evitar problemas
                            payload[col] = value
                        except ValueError:
                            payload[col] = value
                    else:
                        payload[col] = value
        
        # Procesar propiedades custom
        properties = {}
        for col in config['csv_info']['custom_columns']:
            if col in row and row[col] is not None:
                value = str(row[col]).strip()
                if value:  # Solo procesar si hay un valor no vacío
                    # Remover el prefijo 'custom:' para obtener el nombre de la propiedad
                    property_name = col.replace('custom:', '')
                    properties[property_name] = value
        
        if properties:
            payload["properties"] = properties
        
        return payload
    
    def create_product(self, payload: Dict) -> Dict:
        """Crear un producto individual"""
        url = urljoin(f"{self.api_url}/", self.endpoint)
        
        try:
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return {
                'success': True,
                'data': response.json(),
                'status_code': response.status_code
            }
        except requests.exceptions.RequestException as e:
            error_detail = "Error desconocido"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                except:
                    error_detail = e.response.text
            
            return {
                'success': False,
                'error': str(e),
                'error_detail': error_detail,
                'status_code': getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            }
    
    def create_products_batch(self, config: Dict, delay_seconds: float = 1.0) -> Dict:
        """Crear productos en lote"""
        rows = config['csv_info']['rows']
        results = {
            'total': len(rows),
            'success': 0,
            'already_exists': 0,
            'failed': 0,
            'details': []
        }
        
        print(f"\n🚀 Iniciando creación de {len(rows)} productos...")
        print("-" * 60)
        
        for i, row in enumerate(rows, 1):
            # Crear payload
            try:
                payload = self.row_to_payload(row, config)
                product_name = payload.get('name', payload.get('external_id', f'Producto #{i}'))
                product_id = payload.get('id', 'N/A')
                
                print(f"[{i:02d}/{len(rows):02d}] Creando: {product_name} (ID: {product_id})...", end=" ")
                
                # Crear producto
                result = self.create_product(payload)
                
                if result['success']:
                    print("✅ ÉXITO")
                    results['success'] += 1
                    results['details'].append({
                        'row': i,
                        'name': product_name,
                        'id': product_id,
                        'status': 'success',
                        'api_id': result['data'].get('id'),
                        'payload': payload
                    })
                elif result['status_code'] == 400 and "already exists" in str(result['error_detail']).lower():
                    print("⚠️ YA EXISTE")
                    results['already_exists'] += 1
                    results['details'].append({
                        'row': i,
                        'name': product_name,
                        'id': product_id,
                        'status': 'already_exists',
                        'message': 'Producto ya existe',
                        'payload': payload
                    })
                else:
                    print("❌ ERROR")
                    results['failed'] += 1
                    results['details'].append({
                        'row': i,
                        'name': product_name,
                        'id': product_id,
                        'status': 'failed',
                        'error': result['error'],
                        'error_detail': result['error_detail'],
                        'status_code': result['status_code'],
                        'payload': payload
                    })
                    
                    # Mostrar detalle del error
                    print(f"     Error: {result['error']}")
                    if result['error_detail']:
                        print(f"     Detalle: {result['error_detail']}")
                
                # Delay entre peticiones si no es el último
                if i < len(rows) and delay_seconds > 0:
                    import time
                    time.sleep(delay_seconds)
                    
            except Exception as e:
                print("❌ ERROR (EXCEPCIÓN)")
                results['failed'] += 1
                results['details'].append({
                    'row': i,
                    'name': 'Error en procesamiento',
                    'id': 'N/A',
                    'status': 'failed',
                    'error': str(e),
                    'error_detail': 'Error al procesar fila CSV',
                    'payload': row
                })
                print(f"     Error: {e}")
        
        return results
    
    def show_summary(self, results: Dict):
        """Mostrar resumen de resultados"""
        print("\n" + "=" * 60)
        print("📊 RESUMEN DE CREACIÓN DE PRODUCTOS")
        print("=" * 60)
        print(f"Total de productos: {results['total']}")
        print(f"✅ Creados exitosamente: {results['success']}")
        print(f"⚠️ Ya existían: {results['already_exists']}")
        print(f"❌ Errores: {results['failed']}")
        
        total_ok = results['success'] + results['already_exists']
        if results['total'] > 0:
            success_rate = (total_ok / results['total']) * 100
            print(f"📈 Tasa de éxito total: {success_rate:.1f}%")
        
        if results['failed'] > 0:
            print(f"\n🔍 DETALLES DE ERRORES:")
            print("-" * 40)
            for detail in results['details']:
                if detail['status'] == 'failed':
                    print(f"• Fila {detail['row']}: {detail['name']} (ID: {detail['id']})")
                    print(f"  Error: {detail['error']}")
                    if detail['error_detail']:
                        error_str = str(detail['error_detail'])[:200]
                        print(f"  Detalle: {error_str}...")
        
        if results['success'] > 0:
            print(f"\n✅ PRODUCTOS CREADOS EXITOSAMENTE:")
            print("-" * 40)
            for detail in results['details'][:10]:  # Mostrar solo los primeros 10
                if detail['status'] == 'success':
                    print(f"• {detail['name']} (ID: {detail['id']}, API ID: {detail['api_id']})")
            
            if results['success'] > 10:
                print(f"  ... y {results['success'] - 10} más")
        
        if results['already_exists'] > 0:
            print(f"\n⚠️ PRODUCTOS QUE YA EXISTÍAN:")
            print("-" * 40)
            for detail in results['details'][:5]:  # Mostrar solo los primeros 5
                if detail['status'] == 'already_exists':
                    print(f"• {detail['name']} (ID: {detail['id']})")
            
            if results['already_exists'] > 5:
                print(f"  ... y {results['already_exists'] - 5} más")
        
        print("=" * 60)
    
    def show_preview(self, config: Dict, max_preview: int = 3):
        """Mostrar vista previa de productos a crear"""
        rows = config['csv_info']['rows'][:max_preview]
        
        print(f"\n📋 VISTA PREVIA DE PRODUCTOS A CREAR:")
        print("-" * 50)
        print(f"Configuración:")
        print(f"  Type ID: {config['type_id']}")
        print(f"  Group ID: {config['group_id']}")
        print(f"  Customer ID: {config['customer_id']}")
        print(f"  Total productos: {config['csv_info']['total_rows']}")
        
        print(f"\nPrimeros {len(rows)} productos:")
        for i, row in enumerate(rows, 1):
            try:
                payload = self.row_to_payload(row, config)
                name = payload.get('name', 'Sin nombre')
                product_id = payload.get('id', 'Sin ID')
                external_id = payload.get('external_id', 'Sin external_id')
                
                print(f"  {i}. {name}")
                print(f"     ID: {product_id}, External ID: {external_id}")
                
                if 'properties' in payload:
                    props = ', '.join([f"{k}={v}" for k, v in payload['properties'].items()])
                    print(f"     Propiedades: {props}")
                print()
            except Exception as e:
                print(f"  {i}. Error al procesar fila: {e}")
        
        if config['csv_info']['total_rows'] > max_preview:
            print(f"  ... y {config['csv_info']['total_rows'] - max_preview} productos más")
    
    def run_interactive(self):
        """Ejecutar modo interactivo"""
        try:
            # Obtener configuración del usuario
            config = self.get_user_input()
            
            # Mostrar vista previa
            self.show_preview(config)
            
            # Configurar delay
            try:
                delay_input = input(f"\n⏱️ Delay entre peticiones en segundos (enter para 1.0): ").strip()
                delay_seconds = float(delay_input) if delay_input else 1.0
                if delay_seconds < 0:
                    delay_seconds = 0
            except ValueError:
                print("⚠️ Delay inválido, usando 1.0 segundos")
                delay_seconds = 1.0
            
            # Confirmar
            confirm = input(f"\n¿Proceder con la creación de {config['csv_info']['total_rows']} productos? (s/N): ").strip().lower()
            if confirm not in ['s', 'si', 'sí', 'y', 'yes']:
                print("❌ Operación cancelada por el usuario")
                return
            
            # Crear productos
            results = self.create_products_batch(config, delay_seconds)
            
            # Mostrar resumen
            self.show_summary(results)
            
        except KeyboardInterrupt:
            print("\n\n❌ Operación cancelada por el usuario")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)
    
    def run_batch(self, args):
        """Ejecutar modo batch (por argumentos)"""
        try:
            # Validar archivo CSV
            csv_info = self.validate_csv_file(args.csv_file)
            
            # Configurar sesión
            if not self.setup_session(args.api_url, args.token):
                raise ValueError("No se pudo conectar al API")
            
            # Preparar configuración
            config = {
                'csv_file': args.csv_file,
                'csv_info': csv_info,
                'type_id': args.type_id,
                'group_id': args.group_id,
                'customer_id': args.customer_id
            }
            
            # Mostrar vista previa si se solicita
            if not args.no_preview:
                self.show_preview(config)
                if not args.yes:
                    confirm = input(f"\n¿Proceder? (s/N): ").strip().lower()
                    if confirm not in ['s', 'si', 'sí', 'y', 'yes']:
                        print("❌ Operación cancelada")
                        return
            
            # Crear productos
            delay_seconds = getattr(args, 'delay', 1.0)
            results = self.create_products_batch(config, delay_seconds)
            
            # Mostrar resumen
            self.show_summary(results)
            
            # Exit code según resultados
            sys.exit(0 if results['failed'] == 0 else 1)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description="Crear productos desde template CSV con el API de Kong RFID WMS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:

  Modo interactivo:
    python3 create_products_from_csv.py

  Modo batch:
    python3 create_products_from_csv.py \\
        --csv-file product_rfid_template_load.csv \\
        --api-url https://api.kong-wms.com \\
        --token your_api_token \\
        --type-id 1 \\
        --group-id 86 \\
        --customer-id 35 \\
        --delay 1.5 \\
        --yes

Template CSV:
  - Columnas estándar: id, external_id, name, display_name, ean, etc.
  - Columnas custom: custom:COLOR, custom:TALLA, custom:COLECCION
  - Las columnas custom se convierten en propiedades del producto
        """
    )
    
    # Argumentos opcionales para modo batch
    parser.add_argument('--csv-file', help='Archivo CSV con los productos')
    parser.add_argument('--api-url', help='URL del API')
    parser.add_argument('--token', help='Token de autenticación')
    parser.add_argument('--type-id', type=int, help='Type ID')
    parser.add_argument('--group-id', type=int, help='Group ID')
    parser.add_argument('--customer-id', type=int, help='Customer ID')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay entre peticiones (segundos)')
    parser.add_argument('--yes', '-y', action='store_true', help='No pedir confirmación')
    parser.add_argument('--no-preview', action='store_true', help='No mostrar vista previa')
    
    args = parser.parse_args()
    
    creator = ProductCreatorFromCSV()
    
    # Detectar modo de ejecución
    batch_args = [args.csv_file, args.api_url, args.token, 
                  args.type_id, args.group_id, args.customer_id]
    
    if all(arg is not None for arg in batch_args):
        # Modo batch - todos los argumentos requeridos están presentes
        creator.run_batch(args)
    else:
        # Modo interactivo
        if any(arg is not None for arg in batch_args):
            print("⚠️  Algunos argumentos proporcionados pero no todos los requeridos.")
            print("    Se ejecutará en modo interactivo.\n")
        creator.run_interactive()


if __name__ == "__main__":
    main()
