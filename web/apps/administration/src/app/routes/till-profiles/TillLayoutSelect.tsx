import {
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  SelectChangeEvent,
  SelectProps,
  FormHelperText,
} from "@mui/material";
import { selectTillLayoutAll, useGetTillLayoutsQuery } from "@api";
import * as React from "react";

export interface TillLayoutSelectProps extends Omit<SelectProps, "value" | "onChange" | "margin"> {
  label: string;
  value?: number;
  helperText?: string;
  margin?: SelectProps["margin"] | "normal";
  onChange: (id: number) => void;
}

export const TillLayoutSelect: React.FC<TillLayoutSelectProps> = ({
  label,
  value,
  onChange,
  error,
  helperText,
  margin,
  ...props
}) => {
  const { layouts } = useGetTillLayoutsQuery(undefined, {
    selectFromResult: ({ data, ...rest }) => ({
      ...rest,
      layouts: data ? selectTillLayoutAll(data) : [],
    }),
  });

  const handleChange = (evt: SelectChangeEvent<unknown>) => {
    if (!isNaN(Number(evt.target.value))) {
      onChange(Number(evt.target.value));
    }
  };

  return (
    <FormControl fullWidth margin={margin} error={error}>
      <InputLabel variant={props.variant} id="tillLayoutSelectLabel">
        {label}
      </InputLabel>
      <Select labelId="tillLayoutSelectLabel" value={value ?? ""} onChange={handleChange} {...props}>
        {layouts.map((layout) => (
          <MenuItem key={layout.id} value={layout.id}>
            {layout.name}
          </MenuItem>
        ))}
      </Select>
      {helperText && <FormHelperText sx={{ ml: 0 }}>{helperText}</FormHelperText>}
    </FormControl>
  );
};
