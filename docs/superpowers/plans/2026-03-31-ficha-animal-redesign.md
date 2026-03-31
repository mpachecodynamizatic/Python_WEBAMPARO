# Rediseño ficha de animal + listado de adopción — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enriquecer la ficha de cada animal con galería de fotos, estado sanitario y tags de compatibilidad; rediseñar el listado de adopción con filtros de compatibilidad y tarjetas mejoradas.

**Architecture:** Todo el backend vive en `admin/app.py` (archivo único). Se añade tabla `animal_photos` y 10 columnas a `animals`. El frontend público usa Jinja2 (`animal_public.html`) y JS vanilla (`adopcion.js`). No se añaden dependencias externas.

**Tech Stack:** Flask 3.0, SQLite/PostgreSQL (DatabaseWrapper), Jinja2, JS vanilla, CSS variables existentes.

---

## Mapa de archivos

| Archivo | Cambio |
|---------|--------|
| `admin/app.py` | init_db, api_animals, api_animal_detail, new_animal, edit_animal + 4 rutas nuevas de galería |
| `admin/templates/animal_form.html` | Añadir bloques galería, salud, compatibilidad |
| `admin/templates/animal_public.html` | Rediseño completo: galería, badges, animales similares |
| `pages/adopcion.html` | Añadir checkboxes de compatibilidad al filtro |
| `js/adopcion.js` | Tarjetas sin modal, filtros de compatibilidad, link a /animal/<id> |
| `css/adopcion.css` | Estilos de tarjeta actualizados y badges |

---

## Task 1: Esquema de BD — tabla animal_photos y columnas nuevas en animals

**Files:**
- Modify: `admin/app.py:710-725` (después del bloque `visit_requests`, antes del usuario admin)

- [ ] **Paso 1: Añadir tabla animal_photos e init de columnas en init_db()**

  En `admin/app.py`, localizar el bloque que termina en:
  ```python
          )
      ''')

      # Crear usuario admin por defecto
  ```

  Insertar justo antes de `# Crear usuario admin por defecto`:

  ```python
          # Tabla de fotos adicionales de animales
          cursor.execute(f'''
              CREATE TABLE IF NOT EXISTS animal_photos (
                  id {auto_id},
                  animal_id INTEGER NOT NULL,
                  photo_path TEXT NOT NULL,
                  display_order INTEGER DEFAULT 0,
                  caption TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (animal_id) REFERENCES animals(id)
              )
          ''')

          # Migración: columnas de salud, compatibilidad y urgencia en animals
          health_compat_cols = [
              ('vaccinated',     'BOOLEAN DEFAULT 0',     'BOOLEAN DEFAULT FALSE'),
              ('sterilized',     'BOOLEAN DEFAULT 0',     'BOOLEAN DEFAULT FALSE'),
              ('chipped',        'BOOLEAN DEFAULT 0',     'BOOLEAN DEFAULT FALSE'),
              ('dewormed',       'BOOLEAN DEFAULT 0',     'BOOLEAN DEFAULT FALSE'),
              ('good_with_kids', 'BOOLEAN DEFAULT 0',     'BOOLEAN DEFAULT FALSE'),
              ('good_with_cats', 'BOOLEAN DEFAULT 0',     'BOOLEAN DEFAULT FALSE'),
              ('good_with_dogs', 'BOOLEAN DEFAULT 0',     'BOOLEAN DEFAULT FALSE'),
              ('apartment_ok',   'BOOLEAN DEFAULT 0',     'BOOLEAN DEFAULT FALSE'),
              ('high_energy',    'BOOLEAN DEFAULT 0',     'BOOLEAN DEFAULT FALSE'),
              ('urgent',         'BOOLEAN DEFAULT 0',     'BOOLEAN DEFAULT FALSE'),
          ]
          if not USE_POSTGRES:
              for col, sqlite_def, _ in health_compat_cols:
                  try:
                      cursor.execute(f'ALTER TABLE animals ADD COLUMN {col} {sqlite_def}')
                  except Exception:
                      pass  # columna ya existe
          else:
              for col, _, pg_def in health_compat_cols:
                  try:
                      cursor.execute(f'ALTER TABLE animals ADD COLUMN IF NOT EXISTS {col} {pg_def}')
                  except Exception:
                      pass
  ```

- [ ] **Paso 2: Verificar que el servidor arranca sin errores**

  ```bat
  .\run.bat
  ```
  Esperado: servidor arranca en puerto 5000 sin errores en consola. Las nuevas columnas se crean en la BD (verificar con cualquier cliente SQLite o viendo que el admin no falla al abrir un animal).

- [ ] **Paso 3: Commit**

  ```bash
  git add admin/app.py
  git commit -m "feat: add animal_photos table and health/compatibility columns to animals"
  ```

---

## Task 2: Extender GET /api/animals y GET /api/animals/<id>

**Files:**
- Modify: `admin/app.py:1964-1998` (funciones `api_animals` y `api_animal_detail`)

- [ ] **Paso 1: Reemplazar api_animals() con versión ampliada**

  Localizar `@app.route('/api/animals')` (línea ~1964) y reemplazar la función completa:

  ```python
  @app.route('/api/animals')
  def api_animals():
      """API para obtener animales con fotos, salud y compatibilidad"""
      status = request.args.get('status', 'adoption')
      animal_type = request.args.get('type')
      limit = request.args.get('limit', type=int)
      filter_kids      = request.args.get('kids')
      filter_cats      = request.args.get('cats')
      filter_dogs      = request.args.get('dogs')
      filter_apartment = request.args.get('apartment')
      filter_urgent    = request.args.get('urgent')

      db = get_db()
      if status == 'adoption':
          query = 'SELECT * FROM animals WHERE status IN ("adoption", "reserved")'
          params = []
      else:
          query = 'SELECT * FROM animals WHERE status = ?'
          params = [status]
      if animal_type:
          query += ' AND type = ?'
          params.append(animal_type)
      if filter_kids:
          query += ' AND good_with_kids = 1'
      if filter_cats:
          query += ' AND good_with_cats = 1'
      if filter_dogs:
          query += ' AND good_with_dogs = 1'
      if filter_apartment:
          query += ' AND apartment_ok = 1'
      if filter_urgent:
          query += ' AND urgent = 1'
      query += ' ORDER BY urgent DESC, created_at DESC'
      if limit:
          query += ' LIMIT ?'
          params.append(limit)

      animals = db.execute(query, params).fetchall()
      result = []
      for a in animals:
          animal_dict = dict(a)
          photos = db.execute(
              'SELECT id, photo_path, display_order FROM animal_photos WHERE animal_id = ? ORDER BY display_order',
              (a['id'],)
          ).fetchall()
          animal_dict['photos'] = [dict(p) for p in photos]
          result.append(animal_dict)
      return jsonify({'animals': result})
  ```

- [ ] **Paso 2: Reemplazar api_animal_detail() con versión ampliada**

  Localizar `@app.route('/api/animals/<int:animal_id>')` (línea ~1991) y reemplazar:

  ```python
  @app.route('/api/animals/<int:animal_id>')
  def api_animal_detail(animal_id):
      """API para obtener un animal por ID, incluyendo fotos y campos nuevos"""
      db = get_db()
      animal = db.execute('SELECT * FROM animals WHERE id = ?', (animal_id,)).fetchone()
      if not animal:
          return jsonify({'error': 'Animal no encontrado'}), 404
      animal_dict = dict(animal)
      photos = db.execute(
          'SELECT id, photo_path, display_order FROM animal_photos WHERE animal_id = ? ORDER BY display_order',
          (animal_id,)
      ).fetchall()
      animal_dict['photos'] = [dict(p) for p in photos]
      # Animales similares (mismo tipo, en adopción, excluido el actual)
      similar = db.execute(
          'SELECT id, name, type, image FROM animals WHERE type = ? AND status IN ("adoption","reserved") AND id != ? LIMIT 3',
          (animal['type'], animal_id)
      ).fetchall()
      animal_dict['similar'] = [dict(s) for s in similar]
      return jsonify(animal_dict)
  ```

- [ ] **Paso 3: Verificar en navegador**

  Abrir `http://localhost:5000/api/animals` — la respuesta JSON debe incluir `"photos": []` en cada animal.
  Abrir `http://localhost:5000/api/animals/1` — debe incluir `"photos"`, `"similar"`, `"vaccinated"`, `"good_with_kids"`, etc.

- [ ] **Paso 4: Commit**

  ```bash
  git add admin/app.py
  git commit -m "feat: extend api/animals responses with photos, health and compatibility fields"
  ```

---

## Task 3: Admin backend — guardar campos de salud, compatibilidad y urgencia

**Files:**
- Modify: `admin/app.py:1216-1324` (funciones `new_animal` y `edit_animal`)

- [ ] **Paso 1: Actualizar new_animal() — leer y guardar los nuevos campos**

  En `new_animal()`, localizar justo después de `description = request.form.get('description')` (línea ~1227) y añadir:

  ```python
          vaccinated     = 1 if request.form.get('vaccinated')     else 0
          sterilized     = 1 if request.form.get('sterilized')     else 0
          chipped        = 1 if request.form.get('chipped')        else 0
          dewormed       = 1 if request.form.get('dewormed')       else 0
          good_with_kids = 1 if request.form.get('good_with_kids') else 0
          good_with_cats = 1 if request.form.get('good_with_cats') else 0
          good_with_dogs = 1 if request.form.get('good_with_dogs') else 0
          apartment_ok   = 1 if request.form.get('apartment_ok')   else 0
          high_energy    = 1 if request.form.get('high_energy')    else 0
          urgent         = 1 if request.form.get('urgent')         else 0
  ```

  Luego reemplazar el `db.execute(INSERT ...)` existente:

  ```python
          db.execute('''
              INSERT INTO animals (name, type, age, gender, size, description, image,
                                   vaccinated, sterilized, chipped, dewormed,
                                   good_with_kids, good_with_cats, good_with_dogs,
                                   apartment_ok, high_energy, urgent)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
          ''', (name, animal_type, age, gender, size, description, image_path,
                vaccinated, sterilized, chipped, dewormed,
                good_with_kids, good_with_cats, good_with_dogs,
                apartment_ok, high_energy, urgent))
  ```

- [ ] **Paso 2: Actualizar edit_animal() — leer y guardar los nuevos campos**

  En `edit_animal()`, localizar justo después de `status = request.form.get('status')` (línea ~1278) y añadir los mismos 10 campos:

  ```python
          vaccinated     = 1 if request.form.get('vaccinated')     else 0
          sterilized     = 1 if request.form.get('sterilized')     else 0
          chipped        = 1 if request.form.get('chipped')        else 0
          dewormed       = 1 if request.form.get('dewormed')       else 0
          good_with_kids = 1 if request.form.get('good_with_kids') else 0
          good_with_cats = 1 if request.form.get('good_with_cats') else 0
          good_with_dogs = 1 if request.form.get('good_with_dogs') else 0
          apartment_ok   = 1 if request.form.get('apartment_ok')   else 0
          high_energy    = 1 if request.form.get('high_energy')    else 0
          urgent         = 1 if request.form.get('urgent')         else 0
  ```

  Reemplazar el `db.execute(UPDATE ...)` existente (línea ~1313):

  ```python
          db.execute('''
              UPDATE animals
              SET name=?, type=?, age=?, gender=?, size=?, description=?, status=?, image=?,
                  vaccinated=?, sterilized=?, chipped=?, dewormed=?,
                  good_with_kids=?, good_with_cats=?, good_with_dogs=?,
                  apartment_ok=?, high_energy=?, urgent=?,
                  updated_at=CURRENT_TIMESTAMP
              WHERE id=?
          ''', (name, animal_type, age, gender, size, description, status, image_path,
                vaccinated, sterilized, chipped, dewormed,
                good_with_kids, good_with_cats, good_with_dogs,
                apartment_ok, high_energy, urgent,
                animal_id))
  ```

- [ ] **Paso 3: Verificar en el panel admin**

  Ir a `http://localhost:5000/admin/animals/new`, crear un animal. No debe dar error 500. Los campos nuevos llegan a 0 (sin marcar) porque aún no están en el HTML — eso es correcto por ahora.

- [ ] **Paso 4: Commit**

  ```bash
  git add admin/app.py
  git commit -m "feat: save health, compatibility and urgent fields in new_animal and edit_animal"
  ```

---

## Task 4: Endpoints de galería (backend)

**Files:**
- Modify: `admin/app.py` — añadir 4 rutas después de `delete_animal` (~línea 1341)

- [ ] **Paso 1: Añadir las 4 rutas de gestión de galería**

  Insertar después del bloque `delete_animal` y antes de `# GESTIÓN DE NOTICIAS`:

  ```python
  # ============================================
  # GALERÍA DE FOTOS DE ANIMALES
  # ============================================

  @app.route('/admin/animals/<int:animal_id>/photos', methods=['POST'])
  @login_required
  def admin_animal_add_photo(animal_id):
      """Subir foto adicional al animal"""
      db = get_db()
      if not db.execute('SELECT id FROM animals WHERE id = ?', (animal_id,)).fetchone():
          return jsonify({'error': 'Animal no encontrado'}), 404
      count = db.execute(
          'SELECT COUNT(*) as c FROM animal_photos WHERE animal_id = ?', (animal_id,)
      ).fetchone()['c']
      if count >= 8:
          return jsonify({'error': 'Máximo 8 fotos por animal'}), 400
      if 'photo' not in request.files:
          return jsonify({'error': 'No se envió ninguna foto'}), 400
      file = request.files['photo']
      if not file or not file.filename or not allowed_file(file.filename):
          return jsonify({'error': 'Archivo no válido'}), 400
      filename = secure_filename(file.filename)
      if not filename:
          return jsonify({'error': 'Nombre de archivo no válido'}), 400
      timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
      filename = f"{timestamp}_{filename}"
      fotos_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'fotos')
      os.makedirs(fotos_dir, exist_ok=True)
      filepath = os.path.join(fotos_dir, filename)
      saved = save_image(file, filepath)
      photo_path = 'uploads/fotos/' + os.path.basename(saved)
      next_order = db.execute(
          'SELECT COALESCE(MAX(display_order), -1) + 1 as n FROM animal_photos WHERE animal_id = ?',
          (animal_id,)
      ).fetchone()['n']
      db.execute(
          'INSERT INTO animal_photos (animal_id, photo_path, display_order) VALUES (?, ?, ?)',
          (animal_id, photo_path, next_order)
      )
      db.commit()
      photo = db.execute(
          'SELECT id, photo_path, display_order FROM animal_photos WHERE animal_id = ? ORDER BY id DESC LIMIT 1',
          (animal_id,)
      ).fetchone()
      return jsonify(dict(photo))


  @app.route('/admin/animals/<int:animal_id>/photos/<int:photo_id>', methods=['DELETE'])
  @login_required
  def admin_animal_delete_photo(animal_id, photo_id):
      """Eliminar foto del animal"""
      db = get_db()
      photo = db.execute(
          'SELECT * FROM animal_photos WHERE id = ? AND animal_id = ?', (photo_id, animal_id)
      ).fetchone()
      if not photo:
          return jsonify({'error': 'Foto no encontrada'}), 404
      if photo['photo_path'] and photo['photo_path'].startswith('uploads/'):
          full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), photo['photo_path'])
          if os.path.exists(full_path):
              os.remove(full_path)
      db.execute('DELETE FROM animal_photos WHERE id = ?', (photo_id,))
      db.commit()
      return jsonify({'ok': True})


  @app.route('/admin/animals/<int:animal_id>/photos/reorder', methods=['POST'])
  @login_required
  def admin_animal_reorder_photos(animal_id):
      """Reordenar fotos: JSON body = [{id, order}, ...]"""
      data = request.get_json(silent=True)
      if not data or not isinstance(data, list):
          return jsonify({'error': 'Datos inválidos'}), 400
      db = get_db()
      for item in data:
          db.execute(
              'UPDATE animal_photos SET display_order = ? WHERE id = ? AND animal_id = ?',
              (item['order'], item['id'], animal_id)
          )
      db.commit()
      return jsonify({'ok': True})


  @app.route('/admin/animals/<int:animal_id>/photos/<int:photo_id>/set-primary', methods=['POST'])
  @login_required
  def admin_animal_set_primary_photo(animal_id, photo_id):
      """Establecer foto como imagen principal del animal (animals.image)"""
      db = get_db()
      photo = db.execute(
          'SELECT photo_path FROM animal_photos WHERE id = ? AND animal_id = ?', (photo_id, animal_id)
      ).fetchone()
      if not photo:
          return jsonify({'error': 'Foto no encontrada'}), 404
      db.execute(
          'UPDATE animals SET image = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
          (photo['photo_path'], animal_id)
      )
      db.commit()
      return jsonify({'ok': True})
  ```

- [ ] **Paso 2: Verificar que el servidor arranca**

  ```bat
  .\run.bat
  ```
  Abrir `http://localhost:5000/admin` — debe cargar sin errores.

- [ ] **Paso 3: Commit**

  ```bash
  git add admin/app.py
  git commit -m "feat: add gallery management endpoints for animal photos"
  ```

---

## Task 5: Formulario de admin — UI de galería, salud y compatibilidad

**Files:**
- Modify: `admin/templates/animal_form.html` (reemplazar contenido completo)

- [ ] **Paso 1: Reemplazar animal_form.html**

  ```html
  {% extends "base.html" %}

  {% block title %}{% if animal %}Editar{% else %}Nuevo{% endif %} Animal{% endblock %}
  {% block page_title %}{% if animal %}Editar{% else %}Nuevo{% endif %} Animal{% endblock %}

  {% block content %}
  <style>
  .section-block {
      background: #f8f9fa;
      border-radius: 10px;
      padding: 1.25rem 1.5rem;
      margin-bottom: 1.5rem;
      border-left: 4px solid #dee2e6;
  }
  .section-block.health  { background: #f0faf0; border-left-color: #4caf50; }
  .section-block.compat  { background: #f0f4ff; border-left-color: #5c6bc0; }
  .section-block.gallery { background: #fff8f0; border-left-color: #F4A460; }
  .section-label {
      font-size: 11px;
      text-transform: uppercase;
      font-weight: 700;
      margin-bottom: .75rem;
      letter-spacing: .05em;
  }
  .section-block.health  .section-label { color: #4caf50; }
  .section-block.compat  .section-label { color: #5c6bc0; }
  .section-block.gallery .section-label { color: #F4A460; }
  .check-grid {
      display: flex;
      gap: 1.5rem;
      flex-wrap: wrap;
  }
  .check-grid label {
      display: flex;
      align-items: center;
      gap: .4rem;
      cursor: pointer;
      font-size: .92rem;
  }
  .check-grid input[type=checkbox] { width: 16px; height: 16px; cursor: pointer; }
  /* Galería */
  #photo-gallery {
      display: flex;
      gap: .6rem;
      flex-wrap: wrap;
      margin-bottom: .75rem;
  }
  .photo-thumb {
      position: relative;
      width: 90px;
      height: 90px;
      border-radius: 8px;
      overflow: visible;
  }
  .photo-thumb img {
      width: 90px;
      height: 90px;
      object-fit: cover;
      border-radius: 8px;
      border: 2px solid #ddd;
  }
  .photo-thumb .photo-actions {
      position: absolute;
      top: -8px;
      right: -8px;
      display: flex;
      gap: 2px;
  }
  .photo-thumb .photo-actions button {
      width: 22px;
      height: 22px;
      border-radius: 50%;
      border: none;
      cursor: pointer;
      font-size: 11px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0;
  }
  .btn-del-photo  { background: #e53935; color: white; }
  .btn-star-photo { background: #F4A460; color: white; }
  .btn-up-photo, .btn-down-photo { background: #5c6bc0; color: white; font-size: 10px; }
  .photo-add-btn {
      width: 90px;
      height: 90px;
      border: 2px dashed #F4A460;
      border-radius: 8px;
      background: white;
      color: #F4A460;
      font-size: 28px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
  }
  .photo-add-btn:hover { background: #fff8f0; }
  #photo-upload-input { display: none; }
  </style>

  <form method="POST" enctype="multipart/form-data" id="animalForm">
      <input type="hidden" name="_csrf_token" value="{{ csrf_token() }}">

      <!-- Campos básicos -->
      <div class="form-group">
          <label for="name">Nombre del animal *</label>
          <input type="text" id="name" name="name" value="{% if animal %}{{ animal.name }}{% endif %}" required>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
          <div class="form-group">
              <label for="type">Tipo *</label>
              <select id="type" name="type" required>
                  <option value="">Selecciona tipo</option>
                  <option value="perro" {% if animal and animal.type == 'perro' %}selected{% endif %}>Perro</option>
                  <option value="gato" {% if animal and animal.type == 'gato' %}selected{% endif %}>Gato</option>
              </select>
          </div>
          <div class="form-group">
              <label for="gender">Género *</label>
              <select id="gender" name="gender" required>
                  <option value="">Selecciona género</option>
                  <option value="Macho" {% if animal and animal.gender == 'Macho' %}selected{% endif %}>Macho</option>
                  <option value="Hembra" {% if animal and animal.gender == 'Hembra' %}selected{% endif %}>Hembra</option>
              </select>
          </div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
          <div class="form-group">
              <label for="age">Edad</label>
              <input type="text" id="age" name="age" value="{% if animal %}{{ animal.age }}{% endif %}" placeholder="Ej: 2 años">
          </div>
          <div class="form-group">
              <label for="size">Tamaño</label>
              <select id="size" name="size">
                  <option value="">Selecciona tamaño</option>
                  <option value="Pequeño" {% if animal and animal.size == 'Pequeño' %}selected{% endif %}>Pequeño</option>
                  <option value="Mediano" {% if animal and animal.size == 'Mediano' %}selected{% endif %}>Mediano</option>
                  <option value="Grande" {% if animal and animal.size == 'Grande' %}selected{% endif %}>Grande</option>
              </select>
          </div>
      </div>

      {% if animal %}
      <div class="form-group">
          <label for="status">Estado</label>
          <select id="status" name="status">
              <option value="adoption" {% if animal.status == 'adoption' %}selected{% endif %}>En adopción</option>
              <option value="reserved" {% if animal.status == 'reserved' %}selected{% endif %}>Reservado</option>
              <option value="adopted"  {% if animal.status == 'adopted'  %}selected{% endif %}>Adoptado</option>
              <option value="foster"   {% if animal.status == 'foster'   %}selected{% endif %}>En acogida</option>
          </select>
      </div>
      {% endif %}

      <div class="form-group">
          <label for="description">Descripción / Historia</label>
          <textarea id="description" name="description" placeholder="Cuéntanos sobre el animal, de dónde viene, su carácter…">{% if animal %}{{ animal.description }}{% endif %}</textarea>
      </div>

      <!-- Foto principal -->
      <div class="form-group">
          <label for="image">Foto principal</label>
          <input type="file" id="image" name="image" accept="image/*">
          {% if animal and animal.image %}
          <div style="margin-top: .75rem;">
              {% if animal.image.startswith('data:image/') %}
              <img src="{{ animal.image }}" alt="{{ animal.name }}" style="max-width:200px;border-radius:8px;">
              {% else %}
              <img src="/{{ animal.image }}" alt="{{ animal.name }}" style="max-width:200px;border-radius:8px;"
                   onerror="this.onerror=null;this.src='/images/animales/{{ animal.type }}.svg'">
              {% endif %}
          </div>
          {% elif animal %}
          <div style="margin-top:.75rem;">
              <img src="/images/animales/{{ animal.type }}.svg" alt="{{ animal.name }}" style="max-width:200px;border-radius:8px;">
          </div>
          {% endif %}
      </div>

      <!-- Galería de fotos adicionales (solo al editar) -->
      {% if animal %}
      <div class="section-block gallery">
          <div class="section-label">Galería de fotos adicionales (máx. 8)</div>
          <div id="photo-gallery">
              {% for photo in extra_photos %}
              <div class="photo-thumb" data-photo-id="{{ photo.id }}" data-order="{{ photo.display_order }}">
                  <img src="/{{ photo.photo_path }}" alt="Foto {{ loop.index }}"
                       onerror="this.onerror=null;this.src='/images/animales/{{ animal.type }}.svg'">
                  <div class="photo-actions">
                      <button type="button" class="btn-star-photo" title="Establecer como portada"
                              onclick="setPhotoAsPrimary({{ photo.id }})">★</button>
                      <button type="button" class="btn-up-photo"   title="Subir"
                              onclick="movePhoto({{ photo.id }}, -1)">↑</button>
                      <button type="button" class="btn-down-photo" title="Bajar"
                              onclick="movePhoto({{ photo.id }},  1)">↓</button>
                      <button type="button" class="btn-del-photo"  title="Eliminar"
                              onclick="deletePhoto({{ photo.id }})">✕</button>
                  </div>
              </div>
              {% endfor %}
              <button type="button" class="photo-add-btn" id="addPhotoBtn" title="Añadir foto"
                      onclick="document.getElementById('photo-upload-input').click()">+</button>
          </div>
          <input type="file" id="photo-upload-input" accept="image/*" onchange="uploadPhoto(this)">
          <div id="gallery-msg" style="font-size:.82rem;color:#888;margin-top:.3rem;">
              Haz clic en ★ para establecer una foto como portada · ↑↓ para reordenar
          </div>
      </div>
      {% endif %}

      <!-- Estado sanitario -->
      <div class="section-block health">
          <div class="section-label">Estado sanitario</div>
          <div class="check-grid">
              <label><input type="checkbox" name="vaccinated"  {% if animal and animal.vaccinated  %}checked{% endif %}> Vacunado/a</label>
              <label><input type="checkbox" name="sterilized"  {% if animal and animal.sterilized  %}checked{% endif %}> Esterilizado/a</label>
              <label><input type="checkbox" name="chipped"     {% if animal and animal.chipped     %}checked{% endif %}> Con chip</label>
              <label><input type="checkbox" name="dewormed"    {% if animal and animal.dewormed    %}checked{% endif %}> Desparasitado/a</label>
          </div>
      </div>

      <!-- Compatibilidad -->
      <div class="section-block compat">
          <div class="section-label">Compatibilidad</div>
          <div class="check-grid">
              <label><input type="checkbox" name="good_with_kids" {% if animal and animal.good_with_kids %}checked{% endif %}> 👶 Bueno con niños</label>
              <label><input type="checkbox" name="good_with_cats" {% if animal and animal.good_with_cats %}checked{% endif %}> 🐱 Convive con gatos</label>
              <label><input type="checkbox" name="good_with_dogs" {% if animal and animal.good_with_dogs %}checked{% endif %}> 🐕 Convive con perros</label>
              <label><input type="checkbox" name="apartment_ok"   {% if animal and animal.apartment_ok   %}checked{% endif %}> 🏠 Apto para piso</label>
              <label><input type="checkbox" name="high_energy"    {% if animal and animal.high_energy    %}checked{% endif %}> ⚡ Muy activo</label>
              <label><input type="checkbox" name="urgent"         {% if animal and animal.urgent         %}checked{% endif %}> ⚠️ URGENTE</label>
          </div>
      </div>

      <div style="display: flex; gap: 1rem; margin-top: 2rem;">
          <button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Guardar</button>
          <a href="{{ url_for('list_animals') }}" class="btn" style="background:#95a5a6;color:white;">
              <i class="fas fa-times"></i> Cancelar
          </a>
      </div>
  </form>

  {% if animal %}
  <script>
  const ANIMAL_ID = {{ animal.id }};

  async function uploadPhoto(input) {
      if (!input.files || !input.files[0]) return;
      const formData = new FormData();
      formData.append('photo', input.files[0]);
      input.value = '';
      const msg = document.getElementById('gallery-msg');
      msg.textContent = 'Subiendo foto…';
      try {
          const resp = await fetch(`/admin/animals/${ANIMAL_ID}/photos`, {
              method: 'POST', body: formData
          });
          const data = await resp.json();
          if (!resp.ok) throw new Error(data.error || 'Error');
          addThumbToGallery(data.id, data.photo_path, data.display_order);
          msg.textContent = 'Foto añadida correctamente.';
      } catch (e) {
          msg.textContent = 'Error al subir: ' + e.message;
      }
  }

  function addThumbToGallery(id, path, order) {
      const gallery = document.getElementById('photo-gallery');
      const addBtn  = document.getElementById('addPhotoBtn');
      const thumb = document.createElement('div');
      thumb.className = 'photo-thumb';
      thumb.dataset.photoId = id;
      thumb.dataset.order = order;
      thumb.innerHTML = `
          <img src="/${path}" onerror="this.onerror=null;this.src='/images/animales/perro.svg'">
          <div class="photo-actions">
              <button type="button" class="btn-star-photo" title="Establecer como portada" onclick="setPhotoAsPrimary(${id})">★</button>
              <button type="button" class="btn-up-photo"   onclick="movePhoto(${id}, -1)">↑</button>
              <button type="button" class="btn-down-photo" onclick="movePhoto(${id},  1)">↓</button>
              <button type="button" class="btn-del-photo"  onclick="deletePhoto(${id})">✕</button>
          </div>`;
      gallery.insertBefore(thumb, addBtn);
  }

  async function deletePhoto(photoId) {
      if (!confirm('¿Eliminar esta foto?')) return;
      const resp = await fetch(`/admin/animals/${ANIMAL_ID}/photos/${photoId}`, { method: 'DELETE' });
      if (resp.ok) {
          document.querySelector(`.photo-thumb[data-photo-id="${photoId}"]`)?.remove();
      } else {
          alert('Error al eliminar la foto');
      }
  }

  async function setPhotoAsPrimary(photoId) {
      const resp = await fetch(`/admin/animals/${ANIMAL_ID}/photos/${photoId}/set-primary`, { method: 'POST' });
      if (resp.ok) {
          document.getElementById('gallery-msg').textContent = 'Foto establecida como portada. Guarda el formulario para confirmar.';
      } else {
          alert('Error al establecer la portada');
      }
  }

  function movePhoto(photoId, direction) {
      const thumbs = Array.from(document.querySelectorAll('.photo-thumb'));
      const idx = thumbs.findIndex(t => parseInt(t.dataset.photoId) === photoId);
      if (idx === -1) return;
      const targetIdx = idx + direction;
      if (targetIdx < 0 || targetIdx >= thumbs.length) return;
      const gallery = document.getElementById('photo-gallery');
      const addBtn  = document.getElementById('addPhotoBtn');
      if (direction === -1) {
          gallery.insertBefore(thumbs[idx], thumbs[targetIdx]);
      } else {
          gallery.insertBefore(thumbs[targetIdx], thumbs[idx]);
      }
      // Actualizar display_order en servidor
      const updated = Array.from(document.querySelectorAll('.photo-thumb')).map((t, i) => ({
          id: parseInt(t.dataset.photoId), order: i
      }));
      fetch(`/admin/animals/${ANIMAL_ID}/photos/reorder`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(updated)
      });
  }
  </script>
  {% endif %}
  {% endblock %}
  ```

- [ ] **Paso 2: Actualizar edit_animal() para pasar extra_photos al template**

  En `admin/app.py`, en `edit_animal()`, localizar la última línea del GET:
  ```python
      animal = db.execute('SELECT * FROM animals WHERE id = ?', (animal_id,)).fetchone()
      return render_template('animal_form.html', animal=animal)
  ```
  Reemplazar por:
  ```python
      animal = db.execute('SELECT * FROM animals WHERE id = ?', (animal_id,)).fetchone()
      extra_photos = db.execute(
          'SELECT id, photo_path, display_order FROM animal_photos WHERE animal_id = ? ORDER BY display_order',
          (animal_id,)
      ).fetchall()
      return render_template('animal_form.html', animal=animal, extra_photos=extra_photos)
  ```

- [ ] **Paso 3: Verificar en el panel admin**

  Ir a `http://localhost:5000/admin/animals` → editar un animal existente. Deben verse los tres bloques nuevos (galería, salud, compatibilidad). Subir una foto, verificar que aparece en la galería. Marcar varios checkboxes, guardar, reabrir — los valores deben persistir.

- [ ] **Paso 4: Commit**

  ```bash
  git add admin/templates/animal_form.html admin/app.py
  git commit -m "feat: add gallery UI and health/compatibility checkboxes to admin animal form"
  ```

---

## Task 6: Página pública /animal/<id> — galería, badges, animales similares

**Files:**
- Modify: `admin/templates/animal_public.html`
- Modify: `admin/app.py:2552-2583` (función `public_animal_page`)

- [ ] **Paso 1: Pasar similar animals desde el backend**

  En `admin/app.py`, localizar `public_animal_page`:
  ```python
  @app.route('/animal/<int:animal_id>')
  @app.route('/animal/<int:animal_id>/<slug>')
  def public_animal_page(animal_id, slug=None):
  ```

  Leer su cuerpo actual y reemplazar el bloque completo:

  ```python
  @app.route('/animal/<int:animal_id>')
  @app.route('/animal/<int:animal_id>/<slug>')
  def public_animal_page(animal_id, slug=None):
      db = get_db()
      animal = db.execute('SELECT * FROM animals WHERE id = ?', (animal_id,)).fetchone()
      if not animal:
          abort(404)
      extra_photos = db.execute(
          'SELECT id, photo_path, display_order FROM animal_photos WHERE animal_id = ? ORDER BY display_order',
          (animal_id,)
      ).fetchall()
      similar = db.execute(
          'SELECT id, name, type, image FROM animals WHERE type = ? AND status IN ("adoption","reserved") AND id != ? LIMIT 3',
          (animal['type'], animal_id)
      ).fetchall()
      settings = {row['key']: row['value'] for row in db.execute('SELECT key, value FROM site_settings').fetchall()}
      return render_template('animal_public.html',
                             animal=animal,
                             extra_photos=extra_photos,
                             similar=similar,
                             settings=settings)
  ```

- [ ] **Paso 2: Reemplazar animal_public.html — añadir galería, badges y animales similares**

  Localizar el bloque `<!-- Imagen -->` en la sección `animal-detail-hero` (línea ~171):
  ```html
              <!-- Imagen -->
              <div>
                  {% if animal.image and animal.image.startswith('uploads/') %}
                  <img src="/{{ animal.image }}" alt="{{ animal.name }}" class="animal-hero-img"
                       onerror="...">
                  {% else %}
                  <img src="..." class="animal-hero-img">
                  {% endif %}
              </div>
  ```

  Reemplazar ese `<div>` completo por:

  ```html
              <!-- Galería de fotos -->
              <div>
                  {% set all_photos = ([{'photo_path': animal.image}] if animal.image and animal.image.startswith('uploads/') else []) + (extra_photos | list) %}
                  {% set main_src = ('/'+animal.image) if (animal.image and animal.image.startswith('uploads/')) else ('/images/animales/' + ('gato' if animal.type == 'gato' else 'perro') + '.svg') %}

                  <!-- Foto principal -->
                  <img id="mainPhoto" src="{{ main_src }}" alt="{{ animal.name }}" class="animal-hero-img"
                       style="cursor:{% if extra_photos %}pointer{% else %}default{% endif %};"
                       onerror="this.onerror=null;this.src='/images/animales/{{ 'gato' if animal.type == 'gato' else 'perro' }}.svg'"
                       {% if extra_photos %}onclick="openLightbox(this.src)"{% endif %}>

                  <!-- Thumbnails (solo si hay fotos adicionales) -->
                  {% if extra_photos %}
                  <div style="display:flex;gap:.5rem;margin-top:.6rem;overflow-x:auto;padding-bottom:.25rem;">
                      <!-- Thumbnail de foto principal -->
                      <img src="{{ main_src }}"
                           style="width:60px;height:60px;object-fit:cover;border-radius:6px;cursor:pointer;border:2px solid #F4A460;flex-shrink:0;"
                           onclick="document.getElementById('mainPhoto').src=this.src"
                           onerror="this.onerror=null;this.style.display='none'">
                      {% for photo in extra_photos %}
                      <img src="/{{ photo.photo_path }}"
                           style="width:60px;height:60px;object-fit:cover;border-radius:6px;cursor:pointer;border:2px solid transparent;flex-shrink:0;"
                           onclick="document.getElementById('mainPhoto').src=this.src;document.querySelectorAll('.thumb-row img').forEach(i=>i.style.borderColor='transparent');this.style.borderColor='#F4A460';"
                           class="thumb-row"
                           onerror="this.onerror=null;this.style.display='none'">
                      {% endfor %}
                  </div>
                  {% endif %}
              </div>
  ```

- [ ] **Paso 3: Añadir badges de salud y compatibilidad**

  En `animal_public.html`, localizar la línea `<div class="info-grid">` y añadir justo DESPUÉS del cierre `</div>` de `info-grid` (y antes del bloque `{% if animal.description %}`):

  ```html
                  <!-- Estado sanitario -->
                  {% set health_items = [
                      ('vaccinated',  '✓ Vacunado/a',       True),
                      ('sterilized',  '✓ Esterilizado/a',   True),
                      ('chipped',     '✓ Con chip',         True),
                      ('dewormed',    '✓ Desparasitado/a',  True),
                  ] %}
                  {% set health_true  = health_items | selectattr('2') | list %}
                  {% if animal.vaccinated or animal.sterilized or animal.chipped or animal.dewormed %}
                  <div style="margin-top:1rem;">
                      <div style="font-size:11px;text-transform:uppercase;color:#999;font-weight:700;margin-bottom:.5rem;">Estado sanitario</div>
                      <div style="display:flex;gap:.4rem;flex-wrap:wrap;">
                          {% if animal.vaccinated  %}<span style="background:#e8f5e9;color:#2e7d32;padding:.2rem .55rem;border-radius:20px;font-size:.8rem;font-weight:600;">✓ Vacunado/a</span>{% endif %}
                          {% if animal.sterilized  %}<span style="background:#e8f5e9;color:#2e7d32;padding:.2rem .55rem;border-radius:20px;font-size:.8rem;font-weight:600;">✓ Esterilizado/a</span>{% endif %}
                          {% if animal.chipped     %}<span style="background:#e8f5e9;color:#2e7d32;padding:.2rem .55rem;border-radius:20px;font-size:.8rem;font-weight:600;">✓ Con chip</span>{% endif %}
                          {% if animal.dewormed    %}<span style="background:#e8f5e9;color:#2e7d32;padding:.2rem .55rem;border-radius:20px;font-size:.8rem;font-weight:600;">✓ Desparasitado/a</span>{% endif %}
                          {% if not animal.vaccinated %}<span style="background:#fff8e1;color:#f57f17;padding:.2rem .55rem;border-radius:20px;font-size:.8rem;">⏳ Pendiente vacunar</span>{% endif %}
                      </div>
                  </div>
                  {% endif %}

                  <!-- Compatibilidad -->
                  {% if animal.good_with_kids or animal.good_with_cats or animal.good_with_dogs or animal.apartment_ok or animal.high_energy %}
                  <div style="margin-top:.85rem;">
                      <div style="font-size:11px;text-transform:uppercase;color:#999;font-weight:700;margin-bottom:.5rem;">Compatibilidad</div>
                      <div style="display:flex;gap:.4rem;flex-wrap:wrap;">
                          {% if animal.good_with_kids %}<span style="background:#e3f2fd;color:#1565c0;padding:.2rem .55rem;border-radius:20px;font-size:.8rem;">👶 Bueno con niños</span>{% endif %}
                          {% if animal.good_with_cats %}
                          <span style="background:#e3f2fd;color:#1565c0;padding:.2rem .55rem;border-radius:20px;font-size:.8rem;">🐱 Convive con gatos</span>
                          {% elif not animal.good_with_cats and (animal.good_with_kids or animal.good_with_dogs or animal.apartment_ok) %}
                          <span style="background:#fce4ec;color:#880e4f;padding:.2rem .55rem;border-radius:20px;font-size:.8rem;">🐱 No con gatos</span>
                          {% endif %}
                          {% if animal.good_with_dogs %}
                          <span style="background:#e3f2fd;color:#1565c0;padding:.2rem .55rem;border-radius:20px;font-size:.8rem;">🐕 Convive con perros</span>
                          {% elif not animal.good_with_dogs and (animal.good_with_kids or animal.good_with_cats or animal.apartment_ok) %}
                          <span style="background:#fce4ec;color:#880e4f;padding:.2rem .55rem;border-radius:20px;font-size:.8rem;">🐕 No con perros</span>
                          {% endif %}
                          {% if animal.apartment_ok   %}<span style="background:#e3f2fd;color:#1565c0;padding:.2rem .55rem;border-radius:20px;font-size:.8rem;">🏠 Apto para piso</span>{% endif %}
                          {% if animal.high_energy    %}<span style="background:#fff8e1;color:#f57f17;padding:.2rem .55rem;border-radius:20px;font-size:.8rem;">⚡ Muy activo</span>{% endif %}
                      </div>
                  </div>
                  {% endif %}
  ```

- [ ] **Paso 4: Añadir sección "Animales similares" y lightbox**

  Localizar el cierre `</section>` que sigue al bloque de formularios (línea ~357) y añadir justo antes del cierre `</section>`:

  ```html
              <!-- Animales similares -->
              {% if similar %}
              <div style="margin-top:3rem;padding-top:2rem;border-top:1px solid #eee;">
                  <h3 style="color:#333;margin-bottom:1.25rem;">También podrían interesarte</h3>
                  <div style="display:flex;gap:1rem;flex-wrap:wrap;">
                      {% for s in similar %}
                      {% set s_img = ('/'+s.image) if (s.image and s.image.startswith('uploads/')) else ('/images/animales/'+('gato' if s.type == 'gato' else 'perro')+'.svg') %}
                      <a href="/animal/{{ s.id }}/{{ s.name | lower | replace(' ','-') }}"
                         style="width:150px;background:#f9f9f9;border-radius:12px;overflow:hidden;border:1px solid #eee;text-decoration:none;color:#333;display:block;">
                          <img src="{{ s_img }}" alt="{{ s.name }}"
                               style="width:150px;height:100px;object-fit:cover;display:block;"
                               onerror="this.onerror=null;this.src='/images/animales/{{ 'gato' if s.type == 'gato' else 'perro' }}.svg'">
                          <div style="padding:.6rem .75rem;font-size:.85rem;font-weight:600;">{{ s.name }}</div>
                      </a>
                      {% endfor %}
                  </div>
              </div>
              {% endif %}
  ```

  Añadir también el botón **Compartir** dentro de los CTAs existentes (el bloque `<div style="margin-top:1.5rem; display:flex...">` de la columna derecha), después del botón de visita:

  ```html
                      <button type="button" onclick="shareAnimal('{{ animal.name }}', '{{ request.url }}')"
                              class="btn" style="background:white;border:1px solid #ddd;color:#666;">
                          <i class="fas fa-share-alt"></i> Compartir
                      </button>
  ```

  Y añadir el lightbox y el script de la galería justo antes de `<script src="/js/i18n.js">`:

  ```html
      <!-- Lightbox sencillo -->
      <div id="lightbox" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.9);z-index:9999;align-items:center;justify-content:center;cursor:pointer;" onclick="this.style.display='none'">
          <img id="lightbox-img" style="max-width:90vw;max-height:90vh;border-radius:8px;">
      </div>
      <script>
      function openLightbox(src) {
          document.getElementById('lightbox-img').src = src;
          document.getElementById('lightbox').style.display = 'flex';
      }
      async function shareAnimal(name, url) {
          if (navigator.share) {
              try { await navigator.share({ title: name + ' busca hogar', url }); } catch(e) {}
          } else {
              await navigator.clipboard.writeText(url);
              alert('Enlace copiado al portapapeles');
          }
      }
      </script>
  ```

- [ ] **Paso 5: Verificar la página pública**

  Con al menos un animal que tenga fotos extra y campos de salud marcados, abrir `http://localhost:5000/animal/1`. Verificar:
  - Galería con thumbnails visibles
  - Clic en thumbnail cambia foto principal
  - Badges de salud en verde
  - Badges de compatibilidad en azul
  - Sección "También podrían interesarte" con 1-3 animales

- [ ] **Paso 6: Commit**

  ```bash
  git add admin/templates/animal_public.html admin/app.py
  git commit -m "feat: redesign animal public page with gallery, health and compatibility badges"
  ```

---

## Task 7: Listado de adopción — tarjetas mejoradas y filtros de compatibilidad

**Files:**
- Modify: `pages/adopcion.html` (sección de filtros)
- Modify: `js/adopcion.js` (createAnimalCardDetailed, filterAndDisplayAnimals, initFilters)
- Modify: `css/adopcion.css` (estilos de tarjeta y badges)

- [ ] **Paso 1: Añadir checkboxes de compatibilidad en adopcion.html**

  Localizar en `pages/adopcion.html` el bloque de tamaños (línea ~123) que termina con:
  ```html
              </div>

              <div class="search-box">
  ```

  Insertar después del `</div>` de tamaños y antes de `<div class="search-box">`:

  ```html
              <!-- Filtros de compatibilidad -->
              <div class="filter-buttons compat-filters" style="margin-top:.5rem;gap:1rem;align-items:center;">
                  <span style="font-size:.82rem;color:#888;font-weight:600;">Compatible con:</span>
                  <label class="compat-check"><input type="checkbox" id="compat-kids"> 👶 Niños</label>
                  <label class="compat-check"><input type="checkbox" id="compat-cats"> 🐱 Gatos</label>
                  <label class="compat-check"><input type="checkbox" id="compat-dogs"> 🐕 Perros</label>
                  <label class="compat-check"><input type="checkbox" id="compat-apt">  🏠 Piso</label>
                  <label class="compat-check"><input type="checkbox" id="compat-urgent"> ⚠️ Solo urgentes</label>
              </div>
  ```

  Y dentro de `<style>` de la página (o en `adopcion.css`) añadir:
  ```css
  .compat-filters { display: flex; flex-wrap: wrap; }
  .compat-check { display: flex; align-items: center; gap: .35rem; cursor: pointer; font-size: .85rem; }
  .compat-check input { width: 15px; height: 15px; accent-color: #F4A460; cursor: pointer; }
  ```

- [ ] **Paso 2: Actualizar adopcion.js — estado de filtros de compatibilidad**

  En `js/adopcion.js`, localizar el bloque de variables de estado (~línea 25):
  ```javascript
  let currentStatusTab = 'adoption';
  let currentFilter = 'todos';
  let currentSize = 'todos';
  let searchQuery = '';
  let allAnimals = [];
  ```
  Reemplazar por:
  ```javascript
  let currentStatusTab = 'adoption';
  let currentFilter = 'todos';
  let currentSize = 'todos';
  let searchQuery = '';
  let allAnimals = [];
  let compatFilters = { kids: false, cats: false, dogs: false, apt: false, urgent: false };
  ```

- [ ] **Paso 3: Registrar listeners de compatibilidad en DOMContentLoaded**

  Localizar en `adopcion.js` la función `DOMContentLoaded` (~línea 32):
  ```javascript
  document.addEventListener('DOMContentLoaded', function() {
      initStatusTabs();
      initFilters();
      initSizeFilters();
      initSearch();
      loadAnimals();
  });
  ```
  Reemplazar por:
  ```javascript
  document.addEventListener('DOMContentLoaded', function() {
      initStatusTabs();
      initFilters();
      initSizeFilters();
      initSearch();
      initCompatFilters();
      loadAnimals();
  });
  ```

  Y añadir la nueva función `initCompatFilters` después de `initSearch`:

  ```javascript
  function initCompatFilters() {
      const map = {
          'compat-kids':   'kids',
          'compat-cats':   'cats',
          'compat-dogs':   'dogs',
          'compat-apt':    'apt',
          'compat-urgent': 'urgent',
      };
      Object.entries(map).forEach(function([id, key]) {
          const el = document.getElementById(id);
          if (el) {
              el.addEventListener('change', function() {
                  compatFilters[key] = this.checked;
                  filterAndDisplayAnimals();
              });
          }
      });
  }
  ```

- [ ] **Paso 4: Actualizar filterAndDisplayAnimals para aplicar filtros de compatibilidad**

  Localizar en `adopcion.js` el bloque de filtrado (~línea 147):
  ```javascript
      let filteredAnimals = allAnimals.filter(animal => {
          const typeMatch = currentFilter === 'todos' || animal.type === currentFilter;
          const sizeMatch = currentSize === 'todos' || animal.size === currentSize;
          const searchMatch = searchQuery === '' || animal.name.toLowerCase().includes(searchQuery);
          return typeMatch && sizeMatch && searchMatch;
      });
  ```
  Reemplazar por:
  ```javascript
      let filteredAnimals = allAnimals.filter(function(animal) {
          const typeMatch   = currentFilter === 'todos' || animal.type === currentFilter;
          const sizeMatch   = currentSize === 'todos' || animal.size === currentSize;
          const searchMatch = searchQuery === '' || animal.name.toLowerCase().includes(searchQuery);
          const kidsMatch   = !compatFilters.kids   || animal.good_with_kids;
          const catsMatch   = !compatFilters.cats   || animal.good_with_cats;
          const dogsMatch   = !compatFilters.dogs   || animal.good_with_dogs;
          const aptMatch    = !compatFilters.apt    || animal.apartment_ok;
          const urgentMatch = !compatFilters.urgent || animal.urgent;
          return typeMatch && sizeMatch && searchMatch && kidsMatch && catsMatch && dogsMatch && aptMatch && urgentMatch;
      });
  ```

- [ ] **Paso 5: Actualizar createAnimalCardDetailed — tags visibles, sin modal, link a ficha**

  Localizar `function createAnimalCardDetailed(animal)` (~línea 183) y reemplazar la función completa:

  ```javascript
  function createAnimalCardDetailed(animal) {
      const card = document.createElement('div');
      card.className = 'animal-card';
      card.setAttribute('data-id', animal.id);

      const type = (animal.type === 'gato') ? 'gato' : 'perro';
      const imgSrc = getAnimalImage(animal);
      const fallbackSrc = `../images/animales/${type}.svg`;
      const isReserved = animal.status === 'reserved';
      const photoCount = (animal.photos || []).length;
      const animalUrl  = `/animal/${animal.id}/${animal.name.toLowerCase().replace(/\s+/g, '-')}`;

      // Construir badges de compatibilidad (máx. 3 visibles)
      const tags = [];
      if (animal.good_with_kids) tags.push('👶 Niños');
      if (animal.good_with_cats) tags.push('🐱 Gatos');
      if (animal.good_with_dogs) tags.push('🐕 Perros');
      if (animal.apartment_ok)   tags.push('🏠 Piso');
      if (animal.high_energy)    tags.push('⚡ Activo');
      const visibleTags = tags.slice(0, 3);

      // Badges de salud (solo los que están marcados)
      const healthTags = [];
      if (animal.vaccinated) healthTags.push('✓ Vacunado');
      if (animal.sterilized) healthTags.push('✓ Esterilizado');
      if (animal.chipped)    healthTags.push('✓ Chip');

      const tagsHtml = visibleTags.map(t =>
          `<span class="animal-compat-tag">${t}</span>`
      ).join('');
      const healthHtml = healthTags.slice(0, 2).map(t =>
          `<span class="animal-health-tag">${t}</span>`
      ).join('');

      card.innerHTML = `
          <div style="position:relative;">
              <img src="${imgSrc}" alt="${animal.name}" class="animal-image"
                   onerror="this.onerror=null;this.src='${fallbackSrc}'">
              ${animal.urgent ? '<span class="animal-urgent-badge">⚠ Urgente</span>' : ''}
              ${isReserved    ? '<span class="animal-reserved-badge"><i class="fas fa-lock"></i> Reservado</span>' : ''}
              ${photoCount > 0 ? `<span class="animal-photo-count">📷 ${photoCount + 1}</span>` : ''}
          </div>
          <div class="animal-info">
              <h3 class="animal-name">${animal.name}</h3>
              <div class="animal-details">
                  <p><i class="fas fa-birthday-cake"></i> ${animal.age || 'Edad desconocida'}</p>
                  <p><i class="fas fa-ruler-vertical"></i> ${animal.size || '—'}</p>
              </div>
              <div class="animal-tags-row">
                  ${tagsHtml}${healthHtml}
              </div>
              <a href="${animalUrl}" class="btn btn-primary btn-small" style="margin-top:.75rem;display:inline-block;">
                  <i class="fas fa-info-circle"></i> Ver ficha completa
              </a>
          </div>
      `;

      return card;
  }
  ```

- [ ] **Paso 6: Añadir estilos de los nuevos badges en adopcion.css**

  Abrir `css/adopcion.css` y añadir al final:

  ```css
  /* Badges en tarjetas de adopción */
  .animal-tags-row {
      display: flex;
      flex-wrap: wrap;
      gap: .3rem;
      margin: .5rem 0;
  }
  .animal-compat-tag {
      background: #e3f2fd;
      color: #1565c0;
      padding: .15rem .45rem;
      border-radius: 12px;
      font-size: .72rem;
      font-weight: 500;
  }
  .animal-health-tag {
      background: #e8f5e9;
      color: #2e7d32;
      padding: .15rem .45rem;
      border-radius: 12px;
      font-size: .72rem;
      font-weight: 500;
  }
  .animal-urgent-badge {
      position: absolute;
      top: 10px;
      left: 10px;
      background: #e53935;
      color: white;
      padding: .2rem .6rem;
      border-radius: 20px;
      font-size: .72rem;
      font-weight: 700;
  }
  .animal-reserved-badge {
      position: absolute;
      top: 10px;
      right: 10px;
      background: #FFB347;
      color: white;
      padding: .2rem .6rem;
      border-radius: 20px;
      font-size: .72rem;
      font-weight: 600;
  }
  .animal-photo-count {
      position: absolute;
      bottom: 8px;
      right: 8px;
      background: rgba(0,0,0,.5);
      color: white;
      padding: .15rem .5rem;
      border-radius: 20px;
      font-size: .72rem;
  }
  ```

- [ ] **Paso 7: Verificar la página de adopción**

  Abrir `http://localhost:5000/pages/adopcion.html`. Verificar:
  - Los checkboxes de compatibilidad aparecen en la barra de filtros
  - Las tarjetas muestran tags de compatibilidad y salud
  - Badge "Urgente" aparece en animales marcados como urgentes
  - El botón "Ver ficha completa" navega a `/animal/<id>/nombre` (no abre modal)
  - Marcar "Niños" en los filtros oculta animales sin `good_with_kids`

- [ ] **Paso 8: Incrementar versión del JS para limpiar caché**

  En `pages/adopcion.html`, localizar la línea que carga `adopcion.js` y cambiar la versión:
  ```html
  <script src="../js/adopcion.js?v=4"></script>
  ```

- [ ] **Paso 9: Commit final**

  ```bash
  git add pages/adopcion.html js/adopcion.js css/adopcion.css
  git commit -m "feat: redesign adoption listing with compatibility filters and enriched cards"
  ```
