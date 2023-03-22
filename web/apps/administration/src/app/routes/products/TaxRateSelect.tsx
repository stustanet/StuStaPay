import {
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  SelectChangeEvent,
  SelectProps,
  FormHelperText,
} from "@mui/material";
import { useGetTaxRatesQuery, selectTaxRateAll } from "@api";
import * as React from "react";

export interface TaxRateSelectProps extends Omit<SelectProps, "value" | "onChange" | "margin"> {
  label: string;
  value: string;
  helperText?: string;
  margin?: SelectProps["margin"] | "normal";
  onChange: (name: string) => void;
}

export const TaxRateSelect: React.FC<TaxRateSelectProps> = ({
  label,
  value,
  onChange,
  error,
  helperText,
  margin,
  ...props
}) => {
  const { taxRates } = useGetTaxRatesQuery(undefined, {
    selectFromResult: ({ data, ...rest }) => ({
      ...rest,
      taxRates: data ? selectTaxRateAll(data) : [],
    }),
  });

  const handleChange = (evt: SelectChangeEvent<unknown>) => {
    if (typeof evt.target.value === "string") {
      onChange(evt.target.value);
    }
  };

  return (
    <FormControl fullWidth margin={margin} error={error}>
      <InputLabel variant={props.variant} id="taxRateSelectLabel">
        {label}
      </InputLabel>
      <Select labelId="taxRateSelectLabel" value={value} onChange={handleChange} {...props}>
        {taxRates.map((taxRate) => (
          <MenuItem key={taxRate.name} value={taxRate.name}>
            {taxRate.description} ({taxRate.rate}%)
          </MenuItem>
        ))}
      </Select>
      {helperText && <FormHelperText sx={{ ml: 0 }}>{helperText}</FormHelperText>}
    </FormControl>
  );
};
