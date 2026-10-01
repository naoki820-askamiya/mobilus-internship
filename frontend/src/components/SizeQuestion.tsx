import { useState, FormEvent } from 'react';
import { BotQuestion } from '../types';
import { SIZE_MAX_CM, SIZE_MIN_CM } from '../constants';
import styles from './BotQuestionInput.module.css';

interface SizeValue {
  length_cm: number;
  width_cm: number;
  height_cm: number;
}

interface SizeQuestionProps {
  question: BotQuestion;
  disabled: boolean;
  onSubmitSize: (size: SizeValue) => void;
  onSelect: (value: string) => void;
}

// 入力欄の定義（縦・横・高さ）
const SIZE_FIELDS = [
  { key: 'length_cm', label: '縦' },
  { key: 'width_cm', label: '横' },
  { key: 'height_cm', label: '高さ' },
] as const;

type SizeFieldKey = (typeof SIZE_FIELDS)[number]['key'];

const EMPTY_INPUTS: Record<SizeFieldKey, string> = {
  length_cm: '',
  width_cm: '',
  height_cm: '',
};

/**
 * サイズ入力のBOT質問コンポーネント
 * 三辺の入力に加え、「測り方がわからない」等の選択肢も提示する
 */
export function SizeQuestion({ question, disabled, onSubmitSize, onSelect }: SizeQuestionProps) {
  const [inputs, setInputs] = useState<Record<SizeFieldKey, string>>(EMPTY_INPUTS);
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (disabled) return;

    const parsed = SIZE_FIELDS.map(field => Number(inputs[field.key]));
    const isValid = parsed.every(
      value => Number.isInteger(value) && value >= SIZE_MIN_CM && value <= SIZE_MAX_CM
    );

    if (!isValid) {
      setValidationError(`各辺は${SIZE_MIN_CM}〜${SIZE_MAX_CM}cmの整数で入力してください`);
      return;
    }

    setValidationError(null);
    const [length_cm, width_cm, height_cm] = parsed;
    onSubmitSize({ length_cm, width_cm, height_cm });
    setInputs(EMPTY_INPUTS);
  };

  return (
    <div className={styles.sizeContainer} data-testid="size-question">
      <form className={styles.sizeForm} onSubmit={handleSubmit}>
        <div className={styles.sizeFields}>
          {SIZE_FIELDS.map(field => (
            <label key={field.key} className={styles.sizeField}>
              <span className={styles.sizeLabel}>{field.label}</span>
              <input
                type="number"
                className={styles.sizeInput}
                value={inputs[field.key]}
                min={SIZE_MIN_CM}
                max={SIZE_MAX_CM}
                step={1}
                disabled={disabled}
                onChange={event =>
                  setInputs(prev => ({ ...prev, [field.key]: event.target.value }))
                }
                data-testid={`size-input-${field.key}`}
              />
              <span className={styles.sizeUnit}>cm</span>
            </label>
          ))}
        </div>
        <button
          type="submit"
          className={styles.submitButton}
          disabled={disabled}
          data-testid="size-submit"
        >
          料金を計算する
        </button>
      </form>

      {validationError && <p className={styles.error}>{validationError}</p>}

      <div className={styles.options}>
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
    </div>
  );
}
