import { BotAnswerPayload, BotQuestion } from '../types';
import { BOT_QUESTION_TYPE } from '../constants';
import { ChoiceQuestion } from './ChoiceQuestion';
import { SizeQuestion } from './SizeQuestion';
import styles from './BotQuestionInput.module.css';

interface BotQuestionInputProps {
  question: BotQuestion;
  disabled: boolean;
  error: string | null;
  onAnswer: (payload: BotAnswerPayload) => void;
}

/**
 * BOT質問の入力領域
 * 通常のメッセージ入力欄の代わりに表示し、質問種別に応じたUIへ振り分ける
 */
export function BotQuestionInput({ question, disabled, error, onAnswer }: BotQuestionInputProps) {
  const handleSelect = (value: string) => {
    onAnswer({ type: BOT_QUESTION_TYPE.CHOICE, value });
  };

  return (
    <div className={styles.container} data-testid="bot-question-input">
      {question.type === BOT_QUESTION_TYPE.SIZE ? (
        <SizeQuestion
          question={question}
          disabled={disabled}
          onSelect={handleSelect}
          onSubmitSize={size => onAnswer({ type: BOT_QUESTION_TYPE.SIZE, ...size })}
        />
      ) : (
        <ChoiceQuestion question={question} disabled={disabled} onSelect={handleSelect} />
      )}

      {error && <p className={styles.error}>{error}</p>}
    </div>
  );
}
