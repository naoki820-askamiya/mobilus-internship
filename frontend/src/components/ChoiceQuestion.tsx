import { BotQuestion } from '../types';
import styles from './BotQuestionInput.module.css';

interface ChoiceQuestionProps {
  question: BotQuestion;
  disabled: boolean;
  onSelect: (value: string) => void;
}

/**
 * 選択式のBOT質問コンポーネント
 * 質問文はチャット吹き出しに表示されるため、ここでは選択肢のみを描画する
 */
export function ChoiceQuestion({ question, disabled, onSelect }: ChoiceQuestionProps) {
  return (
    <div className={styles.options} data-testid="choice-question">
      {question.options.map(option => (
        <button
          key={option.value}
          type="button"
          className={styles.optionButton}
          disabled={disabled}
          onClick={() => onSelect(option.value)}
          data-testid={`choice-option-${option.value}`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
