import { forwardRef, type ComponentPropsWithoutRef } from "react";
import { Icone } from "./Icone";

export const AjudaInfo = forwardRef<HTMLButtonElement, ComponentPropsWithoutRef<"button">>(
  function AjudaInfo({ className, children: _children, ...props }, ref) {
    return (
      <button {...props} ref={ref} type="button" className={`ajuda-info${className ? ` ${className}` : ""}`}>
        <Icone nome="info" size={14} aria-hidden="true" />
      </button>
    );
  },
);
