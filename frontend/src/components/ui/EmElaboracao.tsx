import styles from './EmElaboracao.module.css'

interface Props {
  titulo:    string
  descricao: string
  icone?:    string
}

export default function EmElaboracao({ titulo, descricao, icone = '◈' }: Props) {
  return (
    <div className={styles.root}>
      <div className={styles.card}>
        <span className={styles.icone} aria-hidden="true">{icone}</span>
        <h2 className={styles.titulo}>{titulo}</h2>
        <p className={styles.descricao}>{descricao}</p>
        <div className={styles.badge}>Em Elaboração</div>
      </div>
    </div>
  )
}
