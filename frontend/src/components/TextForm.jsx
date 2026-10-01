function TextForm({ dollName, description, onNameChange, onDescriptionChange }) {
  return (
    <div className="field-block">
      <label className="field-label" htmlFor="doll-name">Имя</label>
      <input
        id="doll-name"
        className="text-input"
        type="text"
        value={dollName}
        onChange={(event) => onNameChange(event.target.value)}
        placeholder="Введите имя"
      />

      <label className="field-label field-label--top" htmlFor="description">История / описание</label>
      <textarea
        id="description"
        className="text-area"
        value={description}
        onChange={(event) => onDescriptionChange(event.target.value)}
        placeholder="Введите описание"
        rows={4}
      />
    </div>
  )
}

export default TextForm
