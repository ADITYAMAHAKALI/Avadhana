import type { ButtonHTMLAttributes } from 'react';
import styles from './Button.module.css';

type Variant = 'primary' | 'dark' | 'secondary' | 'ghost';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

const VARIANT_CLASS: Record<Variant, string> = {
  primary: styles.primary,
  dark: styles.dark,
  secondary: styles.secondary,
  ghost: styles.ghost,
};

export function Button({ variant = 'secondary', className, ...rest }: ButtonProps) {
  return <button className={`${styles.base} ${VARIANT_CLASS[variant]} ${className ?? ''}`} {...rest} />;
}
